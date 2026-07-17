# Decisiones técnicas

## Motor sin `tz_aware=True` — usar `core/time.py::as_utc`

**Contexto:** `core/database.py` crea el cliente con `AsyncIOMotorClient(MONGO_URL)`,
sin `tz_aware=True`. BSON guarda los `datetime` en UTC internamente, pero el
driver los devuelve **naive** (sin `tzinfo`) al leerlos, salvo que se
configure explícitamente lo contrario.

**Por qué importa:** cualquier servicio que compare un `datetime` leído de
Mongo contra `datetime.now(timezone.utc)` (ej. checks de expiración/vigencia
de una entidad) lanza `TypeError: can't compare offset-naive and
offset-aware datetimes` si no se protege — un 500 real.

**Decisión:** en vez de tocar la configuración global de Motor (que
afectaría todos los campos `datetime` de toda la app — auth, tokens,
entidades de negocio — un cambio de radio mucho mayor), existe un helper
acotado en `core/time.py`:

```python
def as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
```

Úsalo antes de comparar cualquier `datetime` leído de Mongo. No requiere
tocar nada más.

**Por qué se pospone el fix global:** cambiar `tz_aware=True` en
`core/database.py` es la solución correcta a largo plazo, pero requiere
auditar todos los lugares donde se leen/comparan/serializan campos
`datetime` provenientes de Mongo para evitar regresiones silenciosas. No es
seguro hacerlo "de paso" dentro del scope de una feature nueva — evalúalo
como tarea propia si tu dominio termina con muchas comparaciones de fecha.

---

*Registra aquí cada decisión de arquitectura nueva: contexto, alternativas
descartadas, razón (ver CLAUDE.md, sección "Estándares transversales" y
subagente `arquitecto`).*
