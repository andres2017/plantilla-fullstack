from datetime import datetime, timezone

from fastapi import HTTPException, Request
from pymongo import ReturnDocument

from .database import db


def rate_limiter(action: str, max_attempts: int, window_minutes: int):
    """Dependency factory: limita `max_attempts` requests cada `window_minutes`
    por IP para una `action` dada (ej. "register", "items-write"). Genérico y
    reusable — duplicá el uso en cada entidad nueva junto con su router
    (ver routers/items.py).

    Ventana fija (no deslizante): agrupa requests en buckets de
    `window_minutes` e incrementa el contador del bucket actual de forma
    atómica (`find_one_and_update` con `$inc`), para que requests concurrentes
    no puedan leer el mismo conteo antes de que cualquiera lo incremente. Como
    cualquier ventana fija, un cliente puede rafagear ~2x el límite pegado al
    borde de dos buckets consecutivos -- tradeoff aceptado a cambio de
    simplicidad; si se necesita precisión estricta, migrar a un algoritmo de
    ventana deslizante."""
    async def _dependency(request: Request):
        ip = request.client.host if request.client else "unknown"
        now = datetime.now(timezone.utc)
        bucket = int(now.timestamp() // (window_minutes * 60))
        identifier = f"{action}:{ip}:{bucket}"
        doc = await db.rate_limit_events.find_one_and_update(
            {"identifier": identifier},
            {"$inc": {"count": 1}, "$setOnInsert": {"created_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if doc["count"] > max_attempts:
            raise HTTPException(
                status_code=429,
                detail=f"Demasiadas solicitudes. Intenta en {window_minutes} minuto(s).",
            )
    return _dependency
