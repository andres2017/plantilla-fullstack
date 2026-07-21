# Decisiones técnicas

## 2026-07-20 — Ciclo de auditoría/QA del módulo de pagos: 1 CRÍTICO + 2 ALTO encontrados y cerrados

**Contexto:** primera pasada de `auditor-seguridad` y `qa-lead` (en paralelo)
sobre el módulo de pagos recién implementado (ver entrada de abajo). Ambos
dieron **VETO/RECHAZADO** de forma independiente.

**CRÍTICO (mismo hallazgo, confirmado por los dos agentes por separado):**
`payments/config.py::validate_payments_config()` estaba definida pero
nunca se invocaba desde ningún lado, y `wompi.py::verify_webhook_signature`
usaba `WOMPI_EVENTS_SECRET or ""` como fallback. Combinados: un despliegue
con `PAYMENTS_ENABLED=true` pero sin terminar de configurar las credenciales
de Wompi arrancaba igual, en un estado donde **cualquiera podía forjar un
webhook** (checksum calculable sin conocer ningún secreto) y marcar una
orden como pagada sin pagar. Corrección de dos partes: (1) `server.py`
invoca `validate_payments_config()` dentro de `if PAYMENTS_ENABLED:`, a
nivel de import, antes de registrar el router (fail-fast real, tumba el
proceso al arrancar); (2) fail-closed explícito en `wompi.py`
(`verify_webhook_signature` retorna `False` de inmediato si el secreto es
falsy, `_integrity_signature` levanta `RuntimeError` en vez de interpolar
`None`) como segunda capa independiente, para no depender solo de que nadie
vuelva a olvidar el paso (1).

**ALTO — condición de carrera en `idempotency_key` (hallazgo de `qa-lead`):**
dos requests concurrentes con la misma clave podían hacer que el que
"pierde la carrera" reciba un 500 (`DuplicateKeyError` de Mongo sin
capturar) en vez de la orden ya creada por el que ganó. Corregido con
try/except + re-consulta en `payment_service.create_payment` — el índice
único sigue siendo la garantía real de integridad, esto solo evita que la
colisión se traduzca en un error de servidor.

**ALTO — `amount_in_cents` no numérico en el webhook (hallazgo de
`qa-lead`):** un payload con ese campo como string no parseable (`"abc"`,
etc.) tiraba un 500 sin manejar en `int(amount_cents)`. Corregido con
try/except en `wompi.py::parse_webhook_event`, tratado como evento no
reconocido (200 no-op), mismo camino que cualquier otro payload inválido.

**Además, de la propia revisión durante la implementación (antes de la
auditoría):** orden de operaciones en `handle_webhook` cambiado para
validar monto/moneda ANTES de insertar en `payment_events` — un evento con
monto no coincidente ya no "quema" la clave de idempotencia para siempre.
`idempotency_key=""` ahora rechazado con 422 (antes podía llegar a la capa
de datos). Rate limiting agregado al endpoint de webhook (antes era el
único endpoint de escritura del módulo sin ningún freno).

**Re-verificación:** ambos agentes relanzados con foco en los fixes
específicos (no una auditoría/QA completa desde cero). `auditor-seguridad`
revisó con lupa los 3 puntos de riesgo residual que él mismo planteó
(fail-closed de la firma de integridad, si el catch de `DuplicateKeyError`
podía ocultar una colisión real, si el reordenamiento del webhook abría un
vector de replay/spam de logs) — concluyó que los tres están bien resueltos
o son riesgo residual BAJO/MEDIO ya mitigado por controles existentes.
`qa-lead` repitió los 3 escenarios con evidencia reproducible (arranque sin
credenciales → falla con `RuntimeError`; 5 y 10 requests concurrentes con
la misma `idempotency_key` → 0 errores 500, 1 solo documento en Mongo; 9
variantes de `amount_in_cents` malformado → 0 errores 500, ninguna
transición incorrecta) más una pasada de humo completa (RBAC, reembolso,
`PAYMENTS_ENABLED=false`, 16/16 tests existentes).

**Veredicto final: APROBADO por ambos, sin veto.** Deuda no bloqueante
registrada: (a) sin tests automatizados de regresión para el módulo de
pagos — un refactor futuro podría reintroducir cualquiera de estos 3 bugs
en silencio; (b) el flujo de reembolso no se validó end-to-end contra una
cuenta sandbox real de Wompi (no había una disponible en esta sesión).

## 2026-07-20 — Módulo de pagos opcional (Wompi) — APROBADO

**Contexto:** se necesitaba un módulo de pagos reutilizable, activable por
env var, sin acoplarse a las entidades de dominio de ningún proyecto
específico derivado de esta plantilla.

**Alternativas de pasarela evaluadas por `arquitecto`:** MercadoPago (SDK
oficial en Python, buena cobertura, pero comisión más alta ~3.49% vs
~2.65% y retención de fondos hasta 14 días en cuentas nuevas) y Stripe
(mejor DX del mercado, descartado por no soportar PSE/Nequi, métodos
imprescindibles para el mercado colombiano de consumo masivo).

**Decisión:** **Wompi** como proveedor, por comisión más baja, cobertura
completa PSE+Nequi+tarjetas, y sandbox sin fricción de KYC. Diseño con
capa de adaptador (`PaymentProvider`, patrón puerto/adaptador) para no
acoplar routers/services/repositories/models al proveedor específico —
cambiar de proveedor a futuro es escribir un adaptador nuevo, no
reescribir el módulo.

**Mecanismo de idempotencia (doble capa, no redundante):** índice único
en `payment_events.event_key` (`provider:transaction_id:status`) rechaza
reintentos exactos del webhook; update atómico condicionado a
`status="pendiente"` en `payments` evita que una transición ya aplicada
se repita aunque la primera capa fallara por algún motivo.

**Validación de monto:** doble capa — firma de integridad de Wompi
(anti-tampering en el navegador, Wompi rechaza si el monto fue alterado
client-side) + el webhook se cruza siempre contra el monto registrado en
`Payment` al crear la orden, nunca se confía en el monto que reporta el
evento por sí solo.

**Activación:** `PAYMENTS_ENABLED` (default `false`). `payments/config.py`
lee sus variables con `.get()`, nunca con acceso obligatorio a nivel de
import (a diferencia del resto de `core/config.py`) — deliberado, para
que un proyecto sin credenciales de Wompi configuradas arranque exactamente
igual que hoy con el flag apagado.

**4 decisiones tomadas por el usuario tras revisar el diseño:**
1. **Repo:** `plantilla-fullstack` (no `code_key` — ese repo no tiene caso
   de uso de pagos hoy).
2. **Pasarela:** Wompi (siguiendo la recomendación del arquitecto).
3. **Monto en `POST /payments`:** siempre lo calcula/valida la app
   anfitriona antes de invocar el módulo — nunca un monto libremente
   elegido por un cliente no confiable. El módulo no implementa un modo
   "monto libre".
4. **Formato de error:** el módulo de pagos adopta `{code, message}`
   (ej. `PAY_003_FIRMA_INVALIDA`) en vez del string plano que usa hoy
   `core/responses.py::error_response()` en el resto del proyecto — es
   una excepción acotada a este módulo, no una migración del resto del
   proyecto (esa migración queda como sugerencia pendiente, no aprobada).

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
