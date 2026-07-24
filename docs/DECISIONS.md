# Decisiones técnicas

## 2026-07-23 — Diseño MISIÓN 14: Tablero de builds vía Claude Agent SDK — PROPUESTO, PENDIENTE DE APROBACIÓN DEL USUARIO

**Contexto:** feature nueva para que un admin dispare, desde un dashboard,
una edición de `plantilla-fullstack` guiada por prompt en español, ejecutada
por el Claude Agent SDK sobre un working dir aislado, con progreso en vivo y
descarga de `.zip`. Cada build cobra API real de Anthropic — el diseño debe
acotar gasto ($20/día global, $0.50/build), aislar el Agent SDK del proceso
backend (secretos, filesystem), y garantizar un solo build corriendo a la
vez. El documento completo (arquitectura, modelos, endpoints, contratos,
mapa de pantallas, riesgos) se entregó al usuario en la sesión de diseño;
aquí solo el resumen decisional para memoria institucional.

**Decisiones de arquitectura clave:**

1. **Módulo opcional, mismo patrón que `payments`:** `backend/builds/`
   (config.py, errors.py, indexes.py, models/, repositories/, services/,
   routers/) gateado por `BUILDS_ENABLED` (default `false`), config leída
   con `.get()` (nunca `os.environ[...]` obligatorio a nivel de import),
   `validate_builds_config()` invocada solo si el flag está activo — un
   clon de la plantilla que no usa esta feature arranca exactamente igual
   que hoy. Alternativa descartada: meterlo directo en `routers/`/`services/`
   genéricos — rechazada porque acopla el core de la plantilla a una
   dependencia pesada (Agent SDK, llamadas a Anthropic) que la mayoría de
   proyectos derivados no necesitará.

2. **Formato de error propio `{code, message}`** (`BuildHTTPException`,
   calcado de `payments/errors.py`), en vez del string plano de
   `core/responses.py::error_response()`. Igual justificación que pagos:
   taxonomía de códigos (`BUILD_001_TIMEOUT` … `BUILD_010_COLA_LLENA`) que
   el frontend necesita distinguir programáticamente. Es la segunda vez que
   se adopta este patrón — se sugiere al usuario evaluar a futuro
   convertirlo en el estándar del proyecto (no se hace en esta misión).
   **Ajuste requerido y detectado en esta sesión:** `frontend/src/lib/api.js
   ::getApiError()` hoy SOLO contempla `error` como string; nunca se
   extendió para el objeto `{code,message}` cuando se introdujo en pagos
   (pagos aún no tiene consumo frontend en esta plantilla). `frontend-senior`
   debe extenderlo antes de consumir estos endpoints.

3. **Aislamiento del Agent SDK (decisión fija #2 del usuario):** mismo
   proceso backend, pero `cwd` del SDK apuntando a un working dir dedicado
   por build; `env` del subproceso es un diccionario explícito mínimo
   (`ANTHROPIC_API_KEY` + lo estrictamente necesario), NUNCA
   `os.environ.copy()` — así `JWT_SECRET`/`MONGO_URL`/contraseñas del
   backend principal nunca llegan al subproceso. Copia del repo al working
   dir con denylist explícita (`.env`, `.git/`, `node_modules`, patrones ya
   curados en el `.gitignore` raíz) independiente del filtro de Mongo/Git.
   `allowed_tools` restringido a `Read/Write/Edit/Glob/Grep` — **Bash
   deshabilitado por defecto en v1** (veto a habilitarlo sin controles):
   es el vector de mayor riesgo (fuga de `ANTHROPIC_API_KEY` vía
   `env`/`printenv` hacia un archivo que luego se zipea y entrega al admin,
   exfiltración de red, escape de working dir). Contención real de rutas
   vía hook `can_use_tool`/PreToolUse con `os.path.realpath` (no confiar en
   que `cwd` por sí solo sea una jaula). Escaneo de secretos pre-zip como
   red de seguridad adicional. Alternativa descartada: contenedor
   Docker/gVisor por build — más seguro en teoría, pero Render free/starter
   no ofrece Docker-in-Docker ni sandboxing a nivel de kernel de forma
   simple; se documenta como mejora de v2 si el uso crece.

4. **Progreso en vivo: SSE, no WebSocket.** Es unidireccional
   (servidor→cliente), corre sobre HTTP normal (sin upgrade especial en el
   proxy de Render), `EventSource` con `withCredentials:true` reutiliza las
   cookies httpOnly ya existentes sin inventar un esquema de auth nuevo
   (nunca token en query string). Cancelar es una acción REST aparte
   (`POST /builds/{id}/cancel`), no necesita canal bidireccional.

5. **Concurrencia: lock atómico en Mongo (`build_locks`, doc singleton),
   no un flag en memoria.** Un loop `asyncio` en el proceso intenta
   reclamar el lock; si en el futuro Render escala a más de una instancia,
   el lock sigue siendo la fuente de verdad correcta (solo una instancia
   gana el `find_one_and_update` atómico) — se documenta como supuesto
   operativo para `devops-release`: esta feature asume 1 instancia de
   Render mientras esté activa; si se escala, sigue siendo correcto pero
   menos eficiente (instancias ociosas solo pierden un ciclo de poll).
   Recuperación ante caída/reinicio: en `lifespan`, cualquier build en
   `running` al arrancar se marca `failed` (`BUILD_008`) y el lock se
   libera incondicionalmente.

6. **Corte de costo por build: estructural (`max_turns` + timeout duro),
   no un interrupt exacto en tiempo real garantizado.** No hay certeza, sin
   validarlo contra la versión real del SDK, de que el stream de mensajes
   exponga uso de tokens incremental por turno (necesario para un corte
   exacto a mitad de ejecución). Se documenta como riesgo con plan A
   (interrupt en vivo si el SDK lo permite — mejora) y plan B (adoptado
   como baseline garantizado de v1: `BUILDS_MAX_TURNS=40` +
   `BUILDS_TIMEOUT_SECONDS=600` calibrados para que el peor caso se
   mantenga por debajo del tope por construcción). `backend-senior` debe
   validar esto empíricamente en FASE 2 antes de confiar en el plan A.

7. **Presupuesto diario: "comprometido", no solo "gastado".** El chequeo
   contra `BUILDS_DAILY_BUDGET_USD` (default 20) suma costo real de builds
   terminados hoy MÁS costo estimado de los que están `queued`/`running` —
   evita encolar de más builds que en conjunto excederían el tope aunque
   ninguno haya corrido todavía. Un build en cola que deja de caber cuando
   le toca correr (porque otros gastaron entre tanto) se marca `failed`
   (`BUILD_003`) y se salta, sin bloquear el resto de la cola.
   `BUILDS_MAX_QUEUE_DEPTH=10` como tope adicional independiente.

8. **Estimación de costo previa (heurística, no exacta):** tokens de
   contexto base de la plantilla (fijo, ~10-15k, ya que v1 solo soporta
   `plantilla-fullstack`) + tokens del prompt + bucket de tokens de salida
   por tamaño de prompt (pequeño/mediano/grande), con margen de seguridad
   `BUILDS_ESTIMATE_SAFETY_MARGIN=1.3` (sesga la estimación hacia arriba a
   propósito). Tarifas de Sonnet como variables de entorno
   (`BUILDS_PRICE_INPUT_PER_MTOK_USD`/`BUILDS_PRICE_OUTPUT_PER_MTOK_USD`),
   nunca constantes quemadas — para no requerir cambio de código si
   Anthropic ajusta precios. El estimado NUNCA se confía si viene del
   cliente: `POST /builds` recalcula server-side siempre.

**Deuda técnica explícita del MVP** (no se implementa en v1, no se vende de
más): sin almacenamiento de objetos persistente (zips en disco efímero de
Render, TTL corto, no sobreviven redeploy); Bash deshabilitado (el agente no
corre `npm install`/tests dentro del build); un solo template soportado;
historial de builds compartido entre todos los admins sin aislamiento por
usuario; sin reintento automático; sin panel para ajustar límites en
caliente (requiere redeploy).

**Estado:** diseño entregado al usuario, aún no aprobado. No se ha escrito
ningún código de `backend/builds/` ni `frontend/src/features/builds/`.

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

## 2026-07-23 — Fix: builds fallaban en Windows con "Failed to start Claude Code: " (mensaje vacío)

**Contexto:** los 2 primeros builds en modo Agent SDK real fallaron con
`error_code=BUILD_009_WORKER_ERROR` y `error_message="Failed to start Claude
Code: "` (sin texto tras los dos puntos). Se descartó SDK faltante, permisos
de `work_dir` y error de la API de Anthropic (la clave y el binario `claude`
sí estaban disponibles; la plantilla se copió sin error).

**Causa raíz:** un `str(Exception)` vacío es la firma de `NotImplementedError`
sin argumentos — exactamente lo que `asyncio` lanza en Windows al intentar
spawnear un subproceso bajo `SelectorEventLoop` (solo `ProactorEventLoop`
soporta subprocesos ahí). `uvicorn --reload` en Windows fuerza
`SelectorEventLoop` en el proceso real donde corre la app
(`use_subprocess=True` cuando hay `--reload`, ver `uvicorn/config.py` y
`uvicorn/loops/asyncio.py`). El Agent SDK necesita spawnear el CLI `claude`
como subproceso, y ese spawn es el que fallaba.

**Guía operativa (arranque, scripts, verificación):** `docs/BUILDS.md`.

**Fix aplicado:**
1. `builds/services/agent_runner.py`: chequeo defensivo al inicio de
   `run_agent_build` — si `sys.platform == "win32"` y el loop activo no es
   `ProactorEventLoop`, falla rápido con un mensaje accionable en vez de
   dejar que el SDK genere el mensaje vacío.
2. `builds/services/worker.py`: nuevo `error_code=BUILD_011_WINDOWS_EVENTLOOP`
   para este caso (mismo patrón que la detección existente de `TIMEOUT`).
3. `BuildHistoryTable.jsx`: ahora muestra `error_code`/`error_message` en un
   tooltip sobre el badge cuando `status=failed` (antes no se veía el motivo
   en la UI).

**Cómo evitarlo al probar en modo agente en Windows:** corre uvicorn con
`--loop none` (usa el `ProactorEventLoop` por defecto de Windows en vez del
que fuerza `--reload`), o quita `--reload` mientras pruebas builds reales.
En modo STUB (sin `ANTHROPIC_API_KEY`) no aplica: el stub no spawnea
subprocesos.

**Alternativa descartada:** mover el spawn del Agent SDK a un thread con su
propio `ProactorEventLoop` (robusto ante cualquier configuración de uvicorn,
pero requiere puentear callbacks async entre loops — más riesgo/código del
justificado para un fix de compatibilidad de Windows en dev).

### Actualización 2026-07-23 (mismo día) — el chequeo por `isinstance` no bastaba

**Reporte:** con `start-backend-agent.ps1` (sin `--reload`, `--loop none`)
los builds seguían fallando con `BUILD_011_WINDOWS_EVENTLOOP`.

**Investigación:** reproduje el arranque real (`--loop none`, sin
`--reload`) con un diagnóstico temporal en el lifespan — el loop SÍ era
`ProactorEventLoop`. El chequeo por `isinstance` no era el problema. La
causa real: **procesos `uvicorn` huérfanos de pruebas anteriores seguían
escuchando el puerto 8001**, uno de ellos arrancado con `--reload`
(`SelectorEventLoop`). En Windows, `--reload` corre un proceso "reloader" +
un hijo via `multiprocessing`; parar el proceso de la terminal no siempre
mata al hijo, que se queda respondiendo pedidos con el loop viejo aunque
después arranques `start-backend-agent.ps1` correctamente. Confirmado con
`Get-CimInstance Win32_Process` (el hijo tenía `ParentProcessId` apuntando
al reloader).

**Fix aplicado (más robusto, no dependiente de un solo mecanismo):**
1. `backend/run_agent_server.py` (nuevo): fuerza
   `asyncio.WindowsProactorEventLoopPolicy()` **antes** de que uvicorn cree
   el loop, en vez de confiar solo en la interpretación de `--loop none`
   por parte de uvicorn/asyncio.
2. `agent_runner.py`: el chequeo por `isinstance(loop, ProactorEventLoop)`
   se reemplazó por `_assert_subprocess_capable()` — prueba real con
   `asyncio.create_subprocess_exec` (spawnea `python -c pass` y espera). Solo
   falla con `BUILD_011_WINDOWS_EVENTLOOP` si el spawn de verdad no funciona
   (`NotImplementedError`), no por el nombre de la clase del loop.
3. `worker.py`: el log de arranque del worker ahora incluye la clase del
   loop activo en modo agente (`event loop=ProactorEventLoop`), verificable
   a simple vista sin tocar código.
4. `start-backend-agent.ps1`: arranca vía `run_agent_server.py` en vez de
   `uvicorn` directo, y antes de arrancar avisa si el puerto 8001 ya tiene
   algo escuchando (posible proceso viejo con `--reload`).

Modo STUB sin cambios — no spawnea subprocesos, no le aplica ninguna parte
de este bug.

---

## 2026-07-23 — Rediseño UX de la Fábrica: tipo de entrega + agente + modelo

**Contexto:** el brief pidió acercar la UI de `/builds` a builders tipo
Emergent (sin copiar marca/pixel), pero alineado a la plantilla real: el
usuario final elige tipo de entrega, agente y modelo antes de escribir el
prompt, ve costo/presupuesto antes de confirmar, y el historial debe
mostrar esa config además de descargar el zip correctamente. De paso salió
un bug real: `BuildHistoryTable.jsx` leía `build.zip_available`,
`build.cost_real_usd` — campos que **no existen** en la respuesta de
`GET /builds` (el backend manda `has_zip`, `actual_cost_usd`). El botón de
descarga mostraba "Expiró" siempre, sin importar el estado real del zip.

**Decisiones:**
1. **`template_type` / `agent` / `model` opcionales en el contrato**
   (`BuildCreate`/`BuildEstimateRequest`, `Literal` de Pydantic con
   default), persistidos en el doc de Mongo y devueltos en `BuildPublic`.
   Clientes viejos que no los manden siguen funcionando (`full_stack` /
   `implementer` / `sonnet` por default) — sin breaking change.
2. **Addendum de system prompt por tipo y por agente** en
   `agent_runner.py` (`_TEMPLATE_ADDENDA` / `_AGENT_ADDENDA`), concatenados
   al `_SYSTEM_PROMPT` base. Las reglas obligatorias (capas, sin Bash, 4
   estados) quedan intactas para todos los tipos/agentes — el addendum solo
   acota alcance o foco.
3. **Catálogo de modelos configurable por env** (`BUILDS_MODEL_MAP` en
   `config.py`): alias amigable (`haiku`/`sonnet`/`opus`) → model id real,
   con tarifa propia (`BUILDS_MODEL_PRICING`) para que el estimate refleje
   el modelo elegido, no solo el tamaño del prompt.
4. **`created_by_email` agregado al doc del build** (antes solo se
   guardaba el `_id` del admin, sin forma barata de mostrar quién disparó
   el build en el historial). Se toma de `admin["email"]` ya disponible en
   el request — sin lookup extra.
5. **`has_zip` ahora es `Path(zip_path).is_file()`**, no solo
   `bool(zip_path)` — un zip borrado tras un redeploy ya no se reporta
   como disponible.
6. **Fix del bug de campos** en `BuildHistoryTable.jsx`
   (`zip_available`→`has_zip`, `cost_real_usd`→`actual_cost_usd`) —
   causa real del botón "Expiró" persistente.
7. **`BuildForm.jsx` y `QueueProgressCard.jsx` retirados**, reemplazados
   por `PromptComposer.jsx` + `TemplateTypePicker.jsx` +
   `AgentModelPicker.jsx` (nuevos) y `BuildProgress.jsx` (mismo contenido
   que `QueueProgressCard`, renombrado). `BuildsPage.jsx` pasa a dueño único
   del estado del formulario (tipo, agente, modelo, prompt, estimate) — ya
   no hay un `BuildForm` intermedio.

**Validado en navegador (modo STUB):** flujo completo — chip de tipo,
help text dinámico, hint de "Recomendado" en el select de modelo, ejemplo
precargado por tipo, estimate reflejando el multiplicador de contexto por
`template_type`, confirmación, build corriendo y completando, historial
mostrando costo real, tipo/agente/modelo, `created_by_email` y botón de
descarga activo (no "Expiró").

**Alternativa descartada:** mandar `template_type`/`agent`/`model` como
query params en vez de body — se descartó para mantener un solo contrato
JSON consistente con el resto de la API (`{success, data, error}` ya
opera sobre bodies, no querystrings, para writes).

---

*Registra aquí cada decisión de arquitectura nueva: contexto, alternativas
descartadas, razón (ver CLAUDE.md, sección "Estándares transversales" y
subagente `arquitecto`).*
