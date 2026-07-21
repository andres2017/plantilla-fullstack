# Capa HTTP: parsea input, delega en el service, empaqueta el output.
# Cero logica de negocio ni calculo de firmas aca (eso vive en services/ y providers/).
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response

from core.rate_limit import rate_limiter
from core.security import get_current_user, require_admin
from payments.errors import PaymentHTTPException, payment_success_response
from payments.models.payment import PaymentCreate
from payments.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])

_create_rate_limit = Depends(rate_limiter("payments-create", max_attempts=30, window_minutes=1))
# El webhook es el unico endpoint de escritura sin auth de sesion (la firma
# la reemplaza) -- limite generoso para no interferir con trafico real de
# Wompi, pero sin dejarlo completamente sin freno ante trafico arbitrario
# de internet (nadie mas necesita autenticarse para pegarle).
_webhook_rate_limit = Depends(rate_limiter("payments-webhook", max_attempts=120, window_minutes=1))
_MAX_WEBHOOK_BODY_BYTES = 100 * 1024


def _to_public(payment, checkout=None) -> dict:
    data = {
        "reference": payment.reference,
        "status": payment.status,
        "amount_cents": payment.amount_cents,
        "currency": payment.currency,
        "description": payment.description,
        "paid_at": payment.paid_at,
        "created_at": payment.created_at,
    }
    if checkout is not None:
        data["checkout"] = checkout.model_dump()
    return data


@router.post("", status_code=201, dependencies=[_create_rate_limit])
async def create_payment(data: PaymentCreate, response: Response, user: dict = Depends(get_current_user)):
    payment, checkout, created = await payment_service.create_payment(data, created_by=user["_id"])
    if not created:
        response.status_code = 200  # orden ya existia (idempotency_key repetida), no se creo una nueva
    return payment_success_response(_to_public(payment, checkout))


@router.get("/{reference}")
async def get_payment(reference: str, user: dict = Depends(get_current_user)):
    payment = await payment_service.get_payment(reference, user)
    return payment_success_response(_to_public(payment))


@router.get("")
async def list_payments(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    admin: dict = Depends(require_admin),
):
    payments, total = await payment_service.list_payments(page, limit, status)
    items = [_to_public(p) for p in payments]
    return payment_success_response({
        "items": items,
        "pagination": {"page": page, "limit": limit, "total": total,
                       "total_pages": ceil(total / limit) if limit else 0},
    })


@router.post("/{reference}/refund", status_code=202)
async def refund_payment(reference: str, admin: dict = Depends(require_admin)):
    payment = await payment_service.refund_payment(reference)
    return payment_success_response({"reference": payment.reference, "status": payment.status})


@router.post("/webhook/wompi", dependencies=[_webhook_rate_limit])
async def wompi_webhook(request: Request):
    raw_body = await request.body()
    if len(raw_body) > _MAX_WEBHOOK_BODY_BYTES:
        raise PaymentHTTPException(413, "PAY_003_FIRMA_INVALIDA", "Body demasiado grande")
    ok = await payment_service.handle_webhook(raw_body, dict(request.headers))
    if not ok:
        raise PaymentHTTPException(401, "PAY_003_FIRMA_INVALIDA", "Firma de webhook invalida")
    return payment_success_response({"received": True})
