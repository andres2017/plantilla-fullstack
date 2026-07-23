import asyncio
import json
from math import ceil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, StreamingResponse

from core.rate_limit import rate_limiter
from core.security import require_admin
from builds.errors import build_success_response, BuildHTTPException
from builds.models.build import BuildCreate, BuildEstimateRequest
from builds.services import budget_service, build_service
from builds.repositories import build_repository as repo
from builds.services import worker

router = APIRouter(prefix="/builds", tags=[["builds"]])

_write_rate = Depends(rate_limiter("builds-write", max_attempts=20, window_minutes=1))

TERMINAL = {"completed", "failed", "cancelled"}


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


@router.post("/{build_id}/cancel", dependencies=[_write_rate])
async def cancel_build(build_id: str, admin: dict = Depends(require_admin)):
    build = await build_service.cancel_build(build_id)
    return build_success_response(build)


@router.get("/{build_id}/download")
async def download_build(build_id: str, admin: dict = Depends(require_admin)):
    raw = await repo.get_build_raw(build_id)
    if not raw:
        raise BuildHTTPException(404, "BUILD_001_NO_ENCONTRADO", "Build no encontrado")
    if raw.get("status") != "completed":
        raise BuildHTTPException(
            400, "BUILD_006_SIN_ZIP",
            "El build aun no esta completado o no tiene zip disponible",
        )
    zip_path = raw.get("zip_path")
    if not zip_path or not Path(zip_path).is_file():
        raise BuildHTTPException(
            404, "BUILD_006_SIN_ZIP",
            "Archivo zip no encontrado (puede haber expirado tras un redeploy)",
        )
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"build-{build_id}.zip",
    )


@router.get("/{build_id}/events")
async def build_events(build_id: str, request: Request, admin: dict = Depends(require_admin)):
    """SSE de progreso en vivo. Contrato alineado con useBuildEvents.js."""
    build = await build_service.get_build(build_id)

    async def event_stream():
        q = worker.subscribe(build_id)
        try:
            # Snapshot inicial
            queue_position = None
            if build["status"] == "queued":
                raw = await repo.get_build_raw(build_id)
                if raw:
                    queue_position = await repo.count_queued_before(raw["created_at"]) + 1

            snapshot = {
                "status": build["status"],
                "queue_position": queue_position,
                "progress_log": build_service.parse_progress_log(build.get("events") or []),
            }
            yield _sse("snapshot", snapshot)

            if build["status"] in TERMINAL:
                done = {
                    "status": build["status"],
                    "cost_real_usd": build.get("actual_cost_usd"),
                    "download_url": (
                        f"/api/builds/{build_id}/download"
                        if build["status"] == "completed" and build.get("has_zip")
                        else None
                    ),
                }
                yield _sse("done", done)
                return

            # Escuchar eventos en vivo hasta terminal o desconexion
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # Keep-alive comment para proxies
                    yield ": keepalive\n\n"
                    continue

                yield _sse(msg["event"], msg["data"])
                if msg["event"] == "done":
                    break
        finally:
            worker.unsubscribe(build_id, q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: dict) -> str:
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"
