# Capa de reglas de negocio: validaciones, orquestacion. No conoce HTTP ni Mongo directamente
# (usa el repository). Si tu entidad necesita comparar fechas leidas de Mongo contra
# datetime.now(timezone.utc), envuelve el valor con core.time.as_utc() antes de comparar
# (Motor no esta tz_aware — ver docs/DECISIONS.md).
from fastapi import HTTPException

from models.item import Item, ItemCreate, ItemUpdate
from repositories import item_repository


async def create_item(data: ItemCreate, created_by: str) -> Item:
    item = Item(name=data.name.strip(), description=data.description,
                active=data.active, created_by=created_by)
    item.id = await item_repository.insert(item)
    return item


async def list_items(page: int, limit: int, active: bool | None) -> tuple[list[Item], int]:
    query = {"active": active} if active is not None else {}
    return await item_repository.paginate(query, page, limit)


async def get_item(item_id: str) -> Item:
    item = await item_repository.find_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return item


async def update_item(item_id: str, data: ItemUpdate) -> Item:
    await get_item(item_id)
    fields = data.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    return await item_repository.update(item_id, fields)


async def delete_item(item_id: str):
    await get_item(item_id)
    await item_repository.delete(item_id)
