from bson import ObjectId

from core.database import db
from models.user import UserInDB


async def find_by_email(email: str) -> UserInDB | None:
    return UserInDB.from_mongo(await db.users.find_one({"email": email}))


async def find_by_id(user_id: str) -> UserInDB | None:
    if not ObjectId.is_valid(user_id):
        return None
    return UserInDB.from_mongo(await db.users.find_one({"_id": ObjectId(user_id)}))


async def insert(user: UserInDB) -> str:
    result = await db.users.insert_one(user.to_mongo())
    return str(result.inserted_id)


async def update_password(email: str, password_hash: str):
    await db.users.update_one({"email": email}, {"$set": {"password_hash": password_hash}})
