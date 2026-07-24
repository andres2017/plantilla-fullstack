from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

# Tipo de entrega: que plantilla/alcance tiene el build. Cada uno inyecta un
# addendum distinto al system prompt del agente (ver agent_runner.py) y
# ajusta la heuristica de estimate (ver build_service.py).
TemplateType = Literal["full_stack", "web_landing", "mobile_apk", "backend_only", "custom"]

# Rol del agente dentro del build (mismo system prompt base, distinto foco).
AgentRole = Literal["architect", "implementer", "reviewer", "mobile", "docs"]

# Alias amigable -> model id real (mapeo en config.py, configurable por env).
ModelTier = Literal["haiku", "sonnet", "opus"]


class BuildCreate(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=4000)
    template_type: TemplateType = "full_stack"
    agent: AgentRole = "implementer"
    model: ModelTier = "sonnet"


class BuildEstimateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=4000)
    template_type: TemplateType = "full_stack"
    model: ModelTier = "sonnet"


class BuildPublic(BaseModel):
    id: str
    prompt: str
    status: str  # queued | running | completed | failed | cancelled
    template_type: str = "full_stack"
    agent: str = "implementer"
    model: str = "sonnet"
    estimated_cost_usd: float
    actual_cost_usd: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_by: str
    created_by_email: str = ""
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    events: List[str] = []
