# Capa de acceso a datos: solo lee/escribe Mongo, sin reglas de negocio.
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument

from core.database import db
from payments.models.payment import Payment

COLLECTION = db.payments


async def insert(payment: Payment) -> str:
    result = await COLLECTION.insert_one(payment.to_mongo())
    return str(result.inserted_id)


async def find_by_id(payment_id: str) -> Payment | None:
    if not ObjectId.is_valid(payment_id):
        return None
    return Payment.from_mongo(await COLLECTION.find_one({"_id": ObjectId(payment_id)}))


async def find_by_reference(reference: str) -> Payment | None:
    return Payment.from_mongo(await COLLECTION.find_one({"reference": reference}))


async def find_by_idempotency_key(created_by: str, idempotency_key: str) -> Payment | None:
    return Payment.from_mongo(await COLLECTION.find_one({
        "created_by": created_by,
        "client_idempotency_key": idempotency_key,
    }))


async def paginate(query: dict, page: int, limit: int) -> tuple[list[Payment], int]:
    total = await COLLECTION.count_documents(query)
    cursor = COLLECTION.find(query).sort("created_at", -1).skip((page - 1) * limit).limit(limit)
    payments = [Payment.from_mongo(doc) async for doc in cursor]
    return payments, total


async def try_transition_to_paid(reference: str, provider_reference: str, raw_provider_payload: dict) -> Payment | None:
    """Update atomico condicionado a status='pendiente' -- segunda capa de
    idempotencia independiente del indice unico de payment_events. Devuelve
    None si el documento no estaba en 'pendiente' (ya procesado, evento
    fuera de orden, etc.) -- eso es un no-op esperado, no un error."""
    now = datetime.now(timezone.utc)
    doc = await COLLECTION.find_one_and_update(
        {"reference": reference, "status": "pendiente"},
        {"$set": {
            "status": "pagado", "paid_at": now, "updated_at": now,
            "provider_reference": provider_reference,
            "raw_provider_payload": raw_provider_payload,
        }},
        return_document=ReturnDocument.AFTER,
    )
    return Payment.from_mongo(doc)


async def try_transition_to_failed(reference: str, provider_reference: str, failure_reason: str, raw_provider_payload: dict) -> Payment | None:
    now = datetime.now(timezone.utc)
    doc = await COLLECTION.find_one_and_update(
        {"reference": reference, "status": "pendiente"},
        {"$set": {
            "status": "fallido", "failure_reason": failure_reason, "updated_at": now,
            "provider_reference": provider_reference,
            "raw_provider_payload": raw_provider_payload,
        }},
        return_document=ReturnDocument.AFTER,
    )
    return Payment.from_mongo(doc)


async def try_transition_to_refunded(reference: str) -> Payment | None:
    now = datetime.now(timezone.utc)
    doc = await COLLECTION.find_one_and_update(
        {"reference": reference, "status": "pagado"},
        {"$set": {"status": "reembolsado", "refunded_at": now, "updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    return Payment.from_mongo(doc)
