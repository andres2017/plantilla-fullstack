from datetime import datetime, timezone


def as_utc(dt: datetime) -> datetime:
    """Mongo/Motor no esta configurado con tz_aware=True, por lo que los
    datetime leidos de la DB llegan naive. Usa esto antes de comparar un
    datetime leido de Mongo contra datetime.now(timezone.utc) (ej. checks de
    expiracion/vigencia). Ver docs/DECISIONS.md."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
