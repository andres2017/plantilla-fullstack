from motor.motor_asyncio import AsyncIOMotorClient

from .config import MONGO_URL, DB_NAME

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


async def create_indexes():
    # Genericos (auth) — no tocar al duplicar entidades.
    await db.users.create_index("email", unique=True)
    await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")

    # Entidad de ejemplo "items" — agrega aqui los indices de tus propias
    # entidades siguiendo el mismo patron (campo de filtro/orden frecuente).
    await db.items.create_index([("created_at", -1)])
    await db.items.create_index("created_by")
