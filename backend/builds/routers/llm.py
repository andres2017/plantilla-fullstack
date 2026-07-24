from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.security import require_admin
from builds.errors import build_success_response, BuildHTTPException
from builds.services import llm_settings_service as llm

router = APIRouter(prefix="/builds/llm", tags=["builds-llm"])


class SaveKeyBody(BaseModel):
    api_key: str = Field(..., min_length=20, max_length=256)
    preferred_model: Optional[Literal["haiku", "sonnet", "opus"]] = "sonnet"


class PreferredModelBody(BaseModel):
    preferred_model: Literal["haiku", "sonnet", "opus"]


@router.get("/status")
async def llm_status(admin: dict = Depends(require_admin)):
    data = await llm.get_status(str(admin["_id"]))
    return build_success_response(data)


@router.put("/key")
async def save_key(body: SaveKeyBody, admin: dict = Depends(require_admin)):
    try:
        data = await llm.save_api_key(
            str(admin["_id"]),
            body.api_key,
            preferred_model=body.preferred_model or "sonnet",
        )
    except ValueError as e:
        raise BuildHTTPException(400, "LLM_001_KEY_INVALIDA", str(e))
    return build_success_response(data)


@router.delete("/key")
async def delete_key(admin: dict = Depends(require_admin)):
    data = await llm.clear_api_key(str(admin["_id"]))
    return build_success_response(data)


@router.patch("/model")
async def set_model(body: PreferredModelBody, admin: dict = Depends(require_admin)):
    data = await llm.update_preferred_model(str(admin["_id"]), body.preferred_model)
    return build_success_response(data)
