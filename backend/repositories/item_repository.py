# Capa de acceso a datos: solo lee/escribe Mongo, sin reglas de negocio.
# Duplica este archivo para cada entidad nueva (ver models/item.py).
from bson import ObjectId

from core.database import db
from models.item import Item


async def insert(item: Item) -> str:
    result = await db.items.insert_one(item.to_mongo())
    return str(result.inserted_id)


async def find_by_id(item_id: str) -> Item | None:
    if not ObjectId.is_valid(item_id):
        return None
    return Item.from_mongo(await db.items.find_one({"_id": ObjectId(item_id)}))


async def paginate(query: dict, page: int, limit: int) -> tuple[list[Item], int]:
    total = await db.items.count_documents(query)
    cursor = db.items.find(query).sort("created_at", -1).skip((page - 1) * limit).limit(limit)
    items = [Item.from_mongo(doc) async for doc in cursor]
    return items, total


async def update(item_id: str, fields: dict) -> Item | None:
    await db.items.update_one({"_id": ObjectId(item_id)}, {"$set": fields})
    return await find_by_id(item_id)


async def delete(item_id: str) -> bool:
    result = await db.items.delete_one({"_id": ObjectId(item_id)})
    return result.deleted_count == 1
