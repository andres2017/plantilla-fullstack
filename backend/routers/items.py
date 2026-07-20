# Capa HTTP: parsea input, delega en el service, envuelve el output.
# Convencion de acceso (ajustala a lo que tu entidad necesite):
#   - Lectura (GET): cualquier usuario autenticado -> Depends(get_current_user)
#   - Escritura (POST/PATCH/DELETE): solo admin -> Depends(require_admin)
from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.rate_limit import rate_limiter
from core.responses import success_response, paginated_response
from core.security import get_current_user, require_admin
from models.item import ItemCreate, ItemUpdate
from services import item_service

router = APIRouter(prefix="/items", tags=["items"])

# Rate limit generico de escritura (POST/PATCH/DELETE) por IP. Duplicalo con el
# mismo nombre de accion (o uno propio) al copiar este router para una entidad
# nueva -- ver docs/COMO-USAR-PLANTILLA.md.
_write_rate_limit = Depends(rate_limiter("items-write", max_attempts=30, window_minutes=1))


@router.post("", status_code=201, dependencies=[_write_rate_limit])
async def create_item(data: ItemCreate, user: dict = Depends(require_admin)):
    item = await item_service.create_item(data, created_by=user["_id"])
    return success_response(item.model_dump(mode="json"))


@router.get("")
async def list_items(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100),
                     active: Optional[bool] = None, user: dict = Depends(get_current_user)):
    items, total = await item_service.list_items(page, limit, active)
    return paginated_response([i.model_dump(mode="json") for i in items], total, page, limit)


@router.get("/{item_id}")
async def get_item(item_id: str, user: dict = Depends(get_current_user)):
    item = await item_service.get_item(item_id)
    return success_response(item.model_dump(mode="json"))


@router.patch("/{item_id}", dependencies=[_write_rate_limit])
async def update_item(item_id: str, data: ItemUpdate, user: dict = Depends(require_admin)):
    item = await item_service.update_item(item_id, data)
    return success_response(item.model_dump(mode="json"))


@router.delete("/{item_id}", dependencies=[_write_rate_limit])
async def delete_item(item_id: str, user: dict = Depends(require_admin)):
    await item_service.delete_item(item_id)
    return success_response({"deleted": True})
