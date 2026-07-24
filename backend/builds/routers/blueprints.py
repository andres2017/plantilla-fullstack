from fastapi import APIRouter, Depends, Query

from core.security import require_admin
from builds.errors import build_success_response, BuildHTTPException
from builds.services import blueprints_service
from builds.repositories import build_repository as repo

router = APIRouter(prefix="/blueprints", tags=["blueprints"])


@router.get("")
async def list_blueprints(
    locale: str = Query("es", pattern="^(es|en)$"),
    admin: dict = Depends(require_admin),
):
    return build_success_response(blueprints_service.list_blueprints(locale))


@router.get("/{blueprint_id}")
async def get_blueprint(
    blueprint_id: str,
    locale: str = Query("es", pattern="^(es|en)$"),
    admin: dict = Depends(require_admin),
):
    bp = blueprints_service.get_blueprint(blueprint_id, locale)
    if not bp:
        raise BuildHTTPException(404, "BP_001_NO_ENCONTRADO", "Blueprint no encontrado")
    return build_success_response(bp)


@router.get("/{blueprint_id}/progress")
async def blueprint_progress(
    blueprint_id: str,
    locale: str = Query("es", pattern="^(es|en)$"),
    admin: dict = Depends(require_admin),
):
    if not blueprints_service.get_blueprint(blueprint_id, locale):
        raise BuildHTTPException(404, "BP_001_NO_ENCONTRADO", "Blueprint no encontrado")
    builds = await repo.list_builds_for_progress(created_by=str(admin.get("_id", "")))
    data = blueprints_service.compute_progress(blueprint_id, builds, locale)
    return build_success_response(data)
