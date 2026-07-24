from core.database import db


async def create_build_indexes():
    await db.builds.create_index([("created_at", -1)])
    await db.builds.create_index([("status", 1), ("created_at", -1)])
    # Lock singleton (_id="global"): no se crea indice explicito porque _id
    # ya es unico por defecto en Mongo, y un unique=True explicito sobre _id
    # es invalido ("field 'unique' is not valid for an _id index specification").
