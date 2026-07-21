from pymongo.errors import DuplicateKeyError

from core.database import db
from payments.models.payment_event import PaymentEvent

COLLECTION = db.payment_events


async def try_insert(event: PaymentEvent) -> bool:
    """Intenta insertar el evento. Devuelve False si `event_key` ya existia
    (reintento exacto del mismo webhook -- comportamiento esperado de las
    pasarelas, no un error) sin lanzar excepcion. True si es la primera vez
    que se ve esa combinacion provider:transaction_id:status."""
    try:
        await COLLECTION.insert_one(event.to_mongo())
        return True
    except DuplicateKeyError:
        return False
