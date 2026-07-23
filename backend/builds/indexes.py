from core.database import db


async def create_build_indexes():
    await db.builds.create_index([("created_at", -1)])
    await db.builds.create_index([("status", 1), ("created_at", -1)])
    # Lock singleton: solo un documento con _id="global"
    await db.build_locks.create_index([("_id", 1)], unique=True)
