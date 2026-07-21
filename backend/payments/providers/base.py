from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class CheckoutIntent:
    checkout_url: str
    public_key: str
    integrity_signature: str


@dataclass
class WebhookEvent:
    reference: str  # nuestra referencia propia, ecoada por el proveedor -- clave de correlacion
    provider_transaction_id: str
    # Estado ya mapeado por el adaptador a uno de: "pagado" | "fallido".
    # Eventos intermedios (ej. "PENDING" de Wompi) se representan como
    # mapped_status=None -- el caller debe ignorarlos (no-op, 200 igual).
    mapped_status: Optional[str]
    amount_cents: int
    currency: str
    raw_payload: dict


class PaymentProvider(Protocol):
    """Puerto (patron hexagonal): toda la logica generica del modulo
    (routers, services, repositories, modelos) depende solo de esta
    interfaz, nunca de un proveedor concreto. Cambiar de pasarela =
    escribir un adaptador nuevo que la implemente, sin tocar el resto."""

    async def create_intent(
        self, *, reference: str, amount_cents: int, currency: str, description: str,
    ) -> CheckoutIntent: ...

    def verify_webhook_signature(self, *, raw_body: bytes, headers: dict) -> bool: ...

    def parse_webhook_event(self, *, raw_body: bytes, headers: dict) -> Optional[WebhookEvent]: ...

    async def refund(self, *, provider_reference: str) -> bool: ...
