from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class BuildCreate(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=4000)


class BuildEstimateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=4000)


class BuildPublic(BaseModel):
    id: str
    prompt: str
    status: str  # queued | running | completed | failed | cancelled
    estimated_cost_usd: float
    actual_cost_usd: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_by: str
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    events: List[str] = []
