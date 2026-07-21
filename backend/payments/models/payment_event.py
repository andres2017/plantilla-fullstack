from datetime import datetime, timezone

from pydantic import Field

from models.base import BaseDocument


class PaymentEvent(BaseDocument):
    event_key: str  # f"{provider}:{provider_transaction_id}:{status}" -- unico, base real de la idempotencia
    payment_reference: str
    event_type: str
    payload: dict
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed: bool = False
