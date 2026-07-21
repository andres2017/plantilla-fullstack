from core.database import db


async def create_payment_indexes():
    """Se invoca SOLO si PAYMENTS_ENABLED (ver server.py) -- footprint cero
    en proyectos que no usan el modulo."""
    await db.payments.create_index("reference", unique=True)
    await db.payments.create_index("provider_reference", sparse=True)
    await db.payments.create_index("created_by")
    await db.payments.create_index("status")
    # sparse=True en un indice COMPUESTO solo omite documentos donde faltan
    # TODOS los campos indexados -- si "created_by" existe (siempre, en un
    # endpoint autenticado) pero falta "client_idempotency_key", el
    # documento igual se indexa como (created_by, null), y todo pedido sin
    # idempotency_key de un mismo usuario colisionaria entre si. Un indice
    # PARCIAL (con filtro real) es lo que de verdad excluye esos documentos.
    await db.payments.create_index(
        [("created_by", 1), ("client_idempotency_key", 1)],
        unique=True,
        partialFilterExpression={"client_idempotency_key": {"$exists": True}},
    )
    await db.payment_events.create_index("event_key", unique=True)
    await db.payment_events.create_index("payment_reference")
