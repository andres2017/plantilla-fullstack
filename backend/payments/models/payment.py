from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from models.base import BaseDocument

PaymentStatus = Literal["pendiente", "pagado", "fallido", "reembolsado"]


class Payment(BaseDocument):
    reference: str
    status: PaymentStatus = "pendiente"
    amount_cents: int
    currency: str = "COP"
    description: str
    provider: str = "wompi"
    provider_reference: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_by: Optional[str] = None
    client_idempotency_key: Optional[str] = None
    failure_reason: Optional[str] = None
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    raw_provider_payload: Optional[dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaymentCreate(BaseModel):
    amount_cents: int = Field(gt=0)
    currency: str = Field(default="COP", max_length=3)
    description: str = Field(min_length=2, max_length=200)
    metadata: dict = Field(default_factory=dict)
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=100)


class CheckoutInfo(BaseModel):
    provider: str
    checkout_url: str
    public_key: str
    integrity_signature: str


class PaymentPublic(BaseModel):
    reference: str
    status: PaymentStatus
    amount_cents: int
    currency: str
    description: str
    checkout: Optional[CheckoutInfo] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
