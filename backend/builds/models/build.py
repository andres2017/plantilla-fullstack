from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


TemplateType = Literal["full_stack", "web_landing", "backend_api", "mobile_apk", "custom"]
BuildMode = Literal["learn", "implement"]
AgentRole = Literal["implementer", "architect", "reviewer", "mobile", "docs"]
ModelTier = Literal["haiku", "sonnet", "opus"]
LocaleCode = Literal["es", "en"]


class BuildCreate(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=4000)
    template_type: Optional[TemplateType] = None
    blueprint_step_id: Optional[str] = Field(None, max_length=64)
    blueprint_version: Optional[str] = Field(None, max_length=32)
    mode: BuildMode = "implement"
    agent: Optional[AgentRole] = None
    model: Optional[ModelTier] = None
    locale: LocaleCode = "es"


class BuildEstimateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=4000)
    template_type: Optional[TemplateType] = None
    blueprint_step_id: Optional[str] = Field(None, max_length=64)
    mode: BuildMode = "implement"
    agent: Optional[AgentRole] = None
    model: Optional[ModelTier] = None
    locale: LocaleCode = "es"


class BuildPublic(BaseModel):
    id: str
    prompt: str
    status: str
    estimated_cost_usd: float
    actual_cost_usd: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_by: str
    created_by_email: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    events: List[str] = []
    has_zip: bool = False
    template_type: Optional[str] = None
    blueprint_step_id: Optional[str] = None
    blueprint_version: Optional[str] = None
    mode: Optional[str] = None
    agent: Optional[str] = None
    model: Optional[str] = None
    locale: Optional[str] = None
