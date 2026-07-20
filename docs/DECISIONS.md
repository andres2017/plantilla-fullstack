# Decisiones técnicas

## 2026-07-20 — Primera auditoría de seguridad de la plantilla: A1/A3 + C2/C3/A2 heredados

**Contexto:** esta plantilla nunca había pasado por una auditoría de seguridad
completa. Al revisarla se encontró que tenía la misma deuda que ya había sido
detectada y corregida en `code_key` (una app derivada de una versión anterior
de esta plantilla) pero que nunca se portó de vuelta acá: cookies de sesión
con `secure=False, samesite="lax"` hardcodeado (sin variante segura para
despliegues cross-domain), `fastapi==0.110.1` con 2 CVE HIGH sin parchar en el
rango de starlette que arrastra, y ausencia total de headers de seguridad y
rate limiting (más allá del lockout de login que sí existía).

**Decisión:** se cerraron los 4 hallazgos en una sola sesión, portando el
mismo patrón ya validado en `code_key`:
- `COOKIE_SECURE`/`COOKIE_SAMESITE` configurables por entorno (default
  `false`/`lax`, sin cambio de comportamiento en local) + `CORS_ORIGIN_REGEX`
  opcional, con validación fail-fast si `COOKIE_SAMESITE` es inválido o si es
  `none` sin `COOKIE_SECURE=true`.
- Middleware de headers de seguridad (`X-Content-Type-Options`,
  `X-Frame-Options`, `Content-Security-Policy: default-src 'none'`,
  `Referrer-Policy`, `Cache-Control: no-store` en `/api/auth/*`, `HSTS`
  condicionado a `COOKIE_SECURE`).
- Rate limiting genérico por IP (`core/rate_limit.py`, ventana fija atómica
  vía `find_one_and_update` + `$inc`) aplicado a `POST /auth/register` (5/15min)
  y a los 3 endpoints de escritura de `items` (30/1min). El lockout de login
  (`services/auth_service.py`, 5 intentos/15min por email) ya existía y no se
  tocó.
- `fastapi` subido a `0.139.2`.

Verificado: `pip-audit` limpio, 16/16 tests pasando contra un backend real,
`ruff` limpio en todo lo tocado, rate limit probado manualmente (secuencial y
concurrente). Auditado por `auditor-seguridad`: sin hallazgos CRÍTICO/ALTO,
sin veto.

**Deuda técnica nueva, encontrada durante la misma auditoría (no bloqueante,
documentada a propósito para no repetir el error de dejarla sin registro):**

- **M2 — El rate limiter no es proxy-aware.** `request.client.host` es la IP
  real solo mientras no haya un reverse proxy delante. Si se despliega detrás
  de uno (Render/Railway/Nginx/Cloudflare) sin lanzar Uvicorn con
  `--proxy-headers --forwarded-allow-ips=<IP exacta del proxy>`, el rate limit
  se vuelve un balde compartido por todos los usuarios (peor que no tenerlo).
  Si se activa `--proxy-headers` con `forwarded_allow_ips="*"` (error común en
  PaaS), `X-Forwarded-For` pasa a ser confiado y es trivialmente falsificable
  por el atacante. **Bloqueante de FASE 6** (`devops-release`): cualquier
  deploy real detrás de proxy debe fijar `--forwarded-allow-ips` a la IP
  exacta del proxy, nunca `*`, antes de ir a producción.
- **B2 — CSP `default-src 'none'` rompe `/docs`/`/redoc` si quedan expuestos
  en producción** (cargan JS/CSS de un CDN externo que la CSP bloquea).
  Correcto para una API JSON pura; pendiente decidir si `/docs`/`/redoc`
  deben desactivarse en producción (`docs_url=None` condicionado a un flag de
  entorno) antes de FASE 6.
- **B3 — Sin tests automatizados** para los 2 rate limiters nuevos ni para
  los headers de seguridad (se verificaron a mano en esta sesión). Pendiente
  pedirle a `qa-lead` que agregue esos casos antes de cerrar FASE 5 de
  cualquier app derivada que dependa de estos controles.

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
