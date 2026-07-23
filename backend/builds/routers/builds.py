from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.rate_limit import rate_limiter
from core.security import require_admin
from builds.errors import build_success_response, BuildHTTPException
from builds.models.build import BuildCreate, BuildEstimateRequest
from builds.services import budget_service, build_service

router = APIRouter(prefix="/builds", tags=["builds"])

_write_rate = Depends(rate_limiter("builds-write", max_attempts=20, window_minutes=1))


@router.get("/budget")
async def get_budget(admin: dict = Depends(require_admin)):
    data = await budget_service.get_daily_budget()
    return build_success_response(data)


@router.post("/estimate", dependencies=[_write_rate])
async def estimate(data: BuildEstimateRequest, admin: dict = Depends(require_admin)):
    result = build_service.estimate_cost(data.prompt)
    return build_success_response(result)


@router.post("", status_code=201, dependencies=[_write_rate])
async def create_build(data: BuildCreate, admin: dict = Depends(require_admin)):
    build = await build_service.create_build(data.prompt, created_by=admin["_id"])
    return build_success_response(build)


@router.get("")
async def list_builds(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    status: Optional[str] = Query(None),
    admin: dict = Depends(require_admin),
):
    items, total = await build_service.list_builds(page, limit, status)
    return build_success_response({
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": ceil(total / limit) if limit else 0,
        },
    })


@router.get("/{build_id}")
async def get_build(build_id: str, admin: dict = Depends(require_admin)):
    build = await build_service.get_build(build_id)
    return build_success_response(build)
