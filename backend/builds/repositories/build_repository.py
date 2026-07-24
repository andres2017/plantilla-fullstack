from datetime import datetime, timezone, date
from pathlib import Path
from typing import Optional, List, Tuple
from bson import ObjectId
from core.database import db
from core.time import as_utc


def _to_public(doc: dict) -> dict:
    zip_path = doc.get("zip_path")
    return {
        "id": str(doc["_id"]),
        "prompt": doc["prompt"],
        "status": doc["status"],
        "template_type": doc.get("template_type", "full_stack"),
        "agent": doc.get("agent", "implementer"),
        "model": doc.get("model", "sonnet"),
        "estimated_cost_usd": doc.get("estimated_cost_usd", 0.0),
        "actual_cost_usd": doc.get("actual_cost_usd"),
        "error_code": doc.get("error_code"),
        "error_message": doc.get("error_message"),
        "created_by": doc.get("created_by", ""),
        "created_by_email": doc.get("created_by_email", ""),
        "created_at": as_utc(doc["created_at"]),
        "started_at": as_utc(doc["started_at"]) if doc.get("started_at") else None,
        "finished_at": as_utc(doc["finished_at"]) if doc.get("finished_at") else None,
        "events": doc.get("events", []),
        # Path.is_file() en vez de solo bool(zip_path): el campo en Mongo
        # puede seguir apuntando a un zip que ya no existe (redeploy, limpieza
        # manual del work_dir) — el boton de descarga no debe prometer un
        # archivo que ya no esta.
        "has_zip": bool(zip_path) and Path(zip_path).is_file(),
    }


async def create_build(
    prompt: str,
    estimated_cost: float,
    created_by: str,
    created_by_email: str = "",
    template_type: str = "full_stack",
    agent: str = "implementer",
    model: str = "sonnet",
) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "prompt": prompt,
        "status": "queued",
        "template_type": template_type,
        "agent": agent,
        "model": model,
        "estimated_cost_usd": estimated_cost,
        "actual_cost_usd": None,
        "error_code": None,
        "error_message": None,
        "created_by": created_by,
        "created_by_email": created_by_email,
        "created_at": now,
        "started_at": None,
        "finished_at": None,
        "events": [],
        "work_dir": None,
        "zip_path": None,
    }
    result = await db.builds.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_public(doc)


async def get_build(build_id: str) -> Optional[dict]:
    if not ObjectId.is_valid(build_id):
        return None
    doc = await db.builds.find_one({"_id": ObjectId(build_id)})
    return _to_public(doc) if doc else None


async def get_build_raw(build_id: str) -> Optional[dict]:
    """Documento completo (incluye zip_path/work_dir) para uso interno."""
    if not ObjectId.is_valid(build_id):
        return None
    return await db.builds.find_one({"_id": ObjectId(build_id)})


async def list_builds(page: int, limit: int, status: Optional[str] = None) -> Tuple[List[dict], int]:
    query = {}
    if status:
        query["status"] = status
    total = await db.builds.count_documents(query)
    cursor = (
        db.builds.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    items = [_to_public(d) async for d in cursor]
    return items, total


async def update_build(build_id: str, **fields) -> Optional[dict]:
    if not ObjectId.is_valid(build_id):
        return None
    # Permitir None explicitamente en algunos campos (ej. error_code al cancelar)
    if not fields:
        return await get_build(build_id)
    await db.builds.update_one({"_id": ObjectId(build_id)}, {"$set": fields})
    return await get_build(build_id)


async def append_event(build_id: str, event: str):
    if not ObjectId.is_valid(build_id):
        return
    await db.builds.update_one(
        {"_id": ObjectId(build_id)},
        {"$push": {"events": event}},
    )


async def get_today_spent_and_committed() -> tuple[float, float]:
    """Gastado real de builds terminados hoy + estimado de queued/running."""
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    pipeline_spent = [
        {"$match": {
            "status": {"$in": ["completed", "failed"]},
            "finished_at": {"$gte": today_start},
            "actual_cost_usd": {"$ne": None},
        }},
        {"$group": {"_id": None, "total": {"$sum": "$actual_cost_usd"}}},
    ]
    spent_cursor = await db.builds.aggregate(pipeline_spent).to_list(1)
    spent = float(spent_cursor[0]["total"]) if spent_cursor else 0.0

    pipeline_committed = [
        {"$match": {"status": {"$in": ["queued", "running"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$estimated_cost_usd"}}},
    ]
    committed_cursor = await db.builds.aggregate(pipeline_committed).to_list(1)
    committed = float(committed_cursor[0]["total"]) if committed_cursor else 0.0

    return spent, committed


async def count_queued() -> int:
    return await db.builds.count_documents({"status": "queued"})


async def count_queued_before(created_at) -> int:
    """Posicion en cola: cuantos queued fueron creados antes que este."""
    return await db.builds.count_documents({
        "status": "queued",
        "created_at": {"$lt": created_at},
    })


async def try_acquire_lock(holder: str) -> bool:
    """Lock atomico singleton. Retorna True solo si este holder lo adquirio."""
    now = datetime.now(timezone.utc)
    # Intentar reclamar un lock libre (o crear el doc si no existe)
    existing = await db.build_locks.find_one({"_id": "global"})
    if existing is None:
        try:
            await db.build_locks.insert_one({
                "_id": "global",
                "locked": True,
                "holder": holder,
                "acquired_at": now,
            })
            return True
        except Exception:
            return False

    if existing.get("locked") and existing.get("holder"):
        return False

    result = await db.build_locks.find_one_and_update(
        {"_id": "global", "locked": {"$ne": True}},
        {"$set": {"locked": True, "holder": holder, "acquired_at": now}},
        return_document=True,
    )
    return result is not None and result.get("holder") == holder


async def release_lock():
    await db.build_locks.update_one(
        {"_id": "global"},
        {"$set": {"locked": False, "holder": None}},
    )


async def recover_stale_builds():
    """Al arrancar: marca running como failed y libera lock."""
    now = datetime.now(timezone.utc)
    await db.builds.update_many(
        {"status": "running"},
        {"$set": {
            "status": "failed",
            "error_code": "BUILD_008_RECOVERED",
            "error_message": "Build interrumpido por reinicio del servidor",
            "finished_at": now,
        }},
    )
    await release_lock()
