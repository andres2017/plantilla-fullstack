import hashlib
import hmac
import json
import logging
from typing import Optional

import httpx

from payments.config import WOMPI_ENV, WOMPI_PUBLIC_KEY, WOMPI_PRIVATE_KEY, WOMPI_EVENTS_SECRET, WOMPI_INTEGRITY_SECRET
from payments.providers.base import CheckoutIntent, WebhookEvent

logger = logging.getLogger("payments.wompi")

_API_BASE = {
    "sandbox": "https://sandbox.wompi.co/v1",
    "production": "https://production.wompi.co/v1",
}

# Estados crudos de Wompi -> estado interno. PENDING/otros no listados no
# transicionan nada (mapped_status=None, no-op deliberado).
_STATUS_MAP = {
    "APPROVED": "pagado",
    "DECLINED": "fallido",
    "ERROR": "fallido",
    "VOIDED": "fallido",
}


def _get_path(data: dict, dotted_path: str):
    """Resuelve 'transaction.status' -> data['transaction']['status']."""
    node = data
    for part in dotted_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


class WompiProvider:
    def __init__(self):
        self._api_base = _API_BASE.get(WOMPI_ENV, _API_BASE["sandbox"])
        self._checkout_base = "https://checkout.wompi.co/p/"

    async def create_intent(
        self, *, reference: str, amount_cents: int, currency: str, description: str,
    ) -> CheckoutIntent:
        # Wompi Web Checkout es un redirect hospedado por Wompi -- no hace
        # falta una llamada HTTP para "crear" la intencion, se arma la URL
        # con los parametros firmados. La transaccion real se crea del lado
        # de Wompi cuando el usuario completa el checkout; nos enteramos
        # via webhook.
        integrity_signature = self._integrity_signature(reference, amount_cents, currency)
        checkout_url = (
            f"{self._checkout_base}?public-key={WOMPI_PUBLIC_KEY}"
            f"&currency={currency}&amount-in-cents={amount_cents}"
            f"&reference={reference}&signature:integrity={integrity_signature}"
        )
        return CheckoutIntent(
            checkout_url=checkout_url,
            public_key=WOMPI_PUBLIC_KEY,
            integrity_signature=integrity_signature,
        )

    def _integrity_signature(self, reference: str, amount_cents: int, currency: str) -> str:
        if not WOMPI_INTEGRITY_SECRET:
            # Fail-closed: nunca construir una firma/checkout con un secreto
            # ausente -- eso produciria una URL de pago "valida" pero con
            # integridad falsa. Segunda capa independiente de
            # validate_payments_config() (ver payments/config.py y server.py).
            raise RuntimeError(
                "WOMPI_INTEGRITY_SECRET no configurado. No se puede generar "
                "un checkout de pago sin ese secreto -- revisa backend/.env."
            )
        raw = f"{reference}{amount_cents}{currency}{WOMPI_INTEGRITY_SECRET}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify_webhook_signature(self, *, raw_body: bytes, headers: dict) -> bool:
        if not WOMPI_EVENTS_SECRET:
            # Fail-closed: sin secreto configurado, CUALQUIER checksum seria
            # calculable por un atacante (la formula quedaria compuesta solo
            # por datos que el propio atacante controla en el body). Rechazar
            # siempre, nunca caer a una firma "vacia" que coincida con nada.
            logger.error("WOMPI_EVENTS_SECRET no configurado -- webhook rechazado sin verificar")
            return False

        try:
            event = json.loads(raw_body)
        except (ValueError, TypeError):
            return False

        signature = event.get("signature") or {}
        properties = signature.get("properties")
        checksum = signature.get("checksum")
        timestamp = event.get("timestamp")
        if not properties or not checksum or timestamp is None:
            return False

        # NOTA: el orden y algoritmo exacto de concatenacion (valores de
        # `properties` en orden + timestamp + secreto, SHA256 hex) sigue el
        # esquema publicado por Wompi al momento de este diseño -- reconfirmar
        # contra la doc vigente ("Eventos -> Verificacion de integridad") al
        # conectar credenciales reales, los proveedores ajustan el detalle
        # sin previo aviso.
        parts = []
        for prop_path in properties:
            value = _get_path(event.get("data", {}), prop_path)
            if value is None:
                return False
            parts.append(str(value))
        parts.append(str(timestamp))
        parts.append(WOMPI_EVENTS_SECRET)

        expected = hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()
        return hmac.compare_digest(expected.lower(), str(checksum).lower())

    def parse_webhook_event(self, *, raw_body: bytes, headers: dict) -> Optional[WebhookEvent]:
        try:
            event = json.loads(raw_body)
        except (ValueError, TypeError):
            return None

        transaction = _get_path(event, "data.transaction")
        if not transaction:
            return None

        raw_status = transaction.get("status")
        amount_cents = transaction.get("amount_in_cents")
        currency = transaction.get("currency")
        provider_transaction_id = transaction.get("id")
        reference = transaction.get("reference")
        if provider_transaction_id is None or amount_cents is None or currency is None or not reference:
            return None

        try:
            amount_cents = int(amount_cents)
        except (TypeError, ValueError):
            # Payload malformado (ej. amount_in_cents no numerico) -- nunca
            # un 500: tratamos como evento no reconocido, mismo camino que
            # cualquier otro payload invalido (no-op, 200 hacia la pasarela).
            return None

        return WebhookEvent(
            reference=str(reference),
            provider_transaction_id=str(provider_transaction_id),
            mapped_status=_STATUS_MAP.get(raw_status),
            amount_cents=amount_cents,
            currency=str(currency),
            raw_payload=event,
        )

    async def refund(self, *, provider_reference: str) -> bool:
        # Wompi expone "voids" para anular una transaccion. Disponibilidad
        # real (total/parcial, ventana de tiempo permitida) debe reconfirmarse
        # contra la doc vigente y la cuenta real -- puede requerir hacerse
        # desde el back-office de Wompi en vez de la API en algunos casos.
        headers = {"Authorization": f"Bearer {WOMPI_PRIVATE_KEY}"}
        url = f"{self._api_base}/transactions/{provider_reference}/voids"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers)
            if response.status_code >= 400:
                logger.error("Wompi refund fallo para %s: %s %s",
                             provider_reference, response.status_code, response.text)
                return False
            return True
        except httpx.HTTPError:
            logger.error("Wompi refund: error de red para %s", provider_reference, exc_info=True)
            return False
