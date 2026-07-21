# Capa de reglas de negocio: valida, orquesta el proveedor + los repositorios.
# No conoce HTTP directamente (lo usa routers/payments.py).
import logging
import uuid

from pymongo.errors import DuplicateKeyError

from payments.config import (
    PAYMENTS_MIN_AMOUNT_CENTS, PAYMENTS_MAX_AMOUNT_CENTS, PAYMENTS_SUPPORTED_CURRENCIES,
)
from payments.errors import PaymentHTTPException
from payments.models.payment import Payment, PaymentCreate, CheckoutInfo
from payments.models.payment_event import PaymentEvent
from payments.providers.factory import get_provider
from payments.repositories import payment_repository, payment_event_repository

logger = logging.getLogger("payments")


def _validate_amount(amount_cents: int, currency: str):
    currency = currency.upper()
    if currency not in PAYMENTS_SUPPORTED_CURRENCIES:
        raise PaymentHTTPException(422, "PAY_001_MONTO_INVALIDO", f"Moneda no soportada: {currency}")
    if not (PAYMENTS_MIN_AMOUNT_CENTS <= amount_cents <= PAYMENTS_MAX_AMOUNT_CENTS):
        raise PaymentHTTPException(
            422, "PAY_001_MONTO_INVALIDO",
            f"amount_cents debe estar entre {PAYMENTS_MIN_AMOUNT_CENTS} y {PAYMENTS_MAX_AMOUNT_CENTS}",
        )
    if currency == "COP" and amount_cents % 100 != 0:
        raise PaymentHTTPException(422, "PAY_001_MONTO_INVALIDO", "amount_cents en COP debe ser multiplo de 100")


async def create_payment(data: PaymentCreate, created_by: str | None) -> tuple[Payment, CheckoutInfo, bool]:
    """Devuelve (payment, checkout, created) -- `created=False` cuando se
    reusa una orden existente por idempotency_key (el caller debe responder
    200 en ese caso, no 201)."""
    currency = data.currency.upper()
    _validate_amount(data.amount_cents, currency)

    if created_by and data.idempotency_key:
        existing = await payment_repository.find_by_idempotency_key(created_by, data.idempotency_key)
        if existing:
            checkout = await _rebuild_checkout(existing)
            return existing, checkout, False

    payment = Payment(
        reference=uuid.uuid4().hex,
        amount_cents=data.amount_cents,
        currency=currency,
        description=data.description.strip(),
        metadata=data.metadata,
        created_by=created_by,
        client_idempotency_key=data.idempotency_key,
    )
    try:
        payment.id = await payment_repository.insert(payment)
    except DuplicateKeyError:
        # Condicion de carrera: dos requests concurrentes con la misma
        # idempotency_key pasaron el check de arriba antes de que cualquiera
        # insertara -- el indice unico parcial de Mongo es la garantia real
        # (nunca hay 2 documentos), esto solo evita que el que pierde la
        # carrera reciba un 500 en vez de la orden que sí se creo.
        existing = await payment_repository.find_by_idempotency_key(created_by, data.idempotency_key)
        if existing:
            checkout = await _rebuild_checkout(existing)
            return existing, checkout, False
        raise  # colision por otro motivo (no deberia pasar) -- no lo ocultes

    checkout = await _rebuild_checkout(payment)
    return payment, checkout, True


async def _rebuild_checkout(payment: Payment) -> CheckoutInfo:
    provider = get_provider()
    intent = await provider.create_intent(
        reference=payment.reference, amount_cents=payment.amount_cents,
        currency=payment.currency, description=payment.description,
    )
    return CheckoutInfo(
        provider=payment.provider, checkout_url=intent.checkout_url,
        public_key=intent.public_key, integrity_signature=intent.integrity_signature,
    )


async def get_payment(reference: str, requester: dict) -> Payment:
    payment = await payment_repository.find_by_reference(reference)
    is_owner = payment and payment.created_by == requester.get("_id")
    is_admin = requester.get("role") == "admin"
    if not payment or not (is_owner or is_admin):
        # Mismo codigo para "no existe" y "no es tuyo" -- no revelar
        # existencia de una orden ajena (anti-IDOR/anti-enumeracion).
        raise PaymentHTTPException(404, "PAY_005_ORDEN_NO_ENCONTRADA", "Orden de pago no encontrada")
    return payment


async def list_payments(page: int, limit: int, status: str | None) -> tuple[list[Payment], int]:
    query = {"status": status} if status else {}
    return await payment_repository.paginate(query, page, limit)


async def handle_webhook(raw_body: bytes, headers: dict) -> bool:
    """Devuelve True si la firma es valida (200, procesado o ya-procesado
    antes -- ambos casos son 200 para la pasarela). Devuelve False solo si
    la firma no valida (401)."""
    provider = get_provider()

    if not provider.verify_webhook_signature(raw_body=raw_body, headers=headers):
        logger.warning("Webhook de pagos con firma invalida, descartado sin tocar la BD")
        return False

    event = provider.parse_webhook_event(raw_body=raw_body, headers=headers)
    if event is None or event.mapped_status is None:
        # Firma valida pero evento no reconocido o intermedio (ej. PENDING):
        # no-op deliberado, igual 200 (la pasarela no debe reintentar).
        return True

    payment = await payment_repository.find_by_reference(event.reference)
    if payment is None:
        logger.error("Webhook de pagos referencia una orden inexistente: %s", event.reference)
        return True  # firma valida, 200 -- no es culpa de la pasarela, pero no hay nada que transicionar

    if payment.amount_cents != event.amount_cents or payment.currency != event.currency:
        # No se registra en payment_events a proposito: si se insertara acá,
        # ese event_key (transaction_id+status) quedaria "consumido" para
        # siempre y un reintento legitimo con datos correctos nunca podria
        # reprocesarse. Al no persistir nada, un evento futuro correcto para
        # esta misma transaccion todavia puede completar la transicion.
        logger.error(
            "ANOMALIA: monto/moneda del webhook no coincide con la orden registrada. "
            "reference=%s esperado=%s%s recibido=%s%s",
            event.reference, payment.amount_cents, payment.currency, event.amount_cents, event.currency,
        )
        return True  # firma valida (200), pero NUNCA transiciona con datos que no cuadran

    event_key = f"wompi:{event.provider_transaction_id}:{event.mapped_status}"
    is_new = await payment_event_repository.try_insert(PaymentEvent(
        event_key=event_key,
        payment_reference=event.reference,
        event_type=event.mapped_status,
        payload=event.raw_payload,
    ))
    if not is_new:
        # Reintento exacto del mismo webhook (comportamiento esperado de
        # las pasarelas si no se responde 2xx a tiempo) -- 200, sin repetir
        # ningun efecto de negocio.
        return True

    if event.mapped_status == "pagado":
        await payment_repository.try_transition_to_paid(
            event.reference, event.provider_transaction_id, event.raw_payload)
    elif event.mapped_status == "fallido":
        await payment_repository.try_transition_to_failed(
            event.reference, event.provider_transaction_id, "Rechazado por la pasarela", event.raw_payload)

    return True


async def refund_payment(reference: str) -> Payment:
    payment = await payment_repository.find_by_reference(reference)
    if not payment:
        raise PaymentHTTPException(404, "PAY_005_ORDEN_NO_ENCONTRADA", "Orden de pago no encontrada")
    if payment.status != "pagado":
        raise PaymentHTTPException(
            409, "PAY_006_ESTADO_INVALIDO_PARA_REEMBOLSO",
            f"Solo se puede reembolsar una orden en estado 'pagado' (actual: '{payment.status}')",
        )

    provider = get_provider()
    ok = await provider.refund(provider_reference=payment.provider_reference or "")
    if not ok:
        raise PaymentHTTPException(502, "PAY_006_ESTADO_INVALIDO_PARA_REEMBOLSO",
                                    "La pasarela no confirmo el reembolso, intenta de nuevo o revisa el back-office")

    updated = await payment_repository.try_transition_to_refunded(reference)
    return updated or payment
