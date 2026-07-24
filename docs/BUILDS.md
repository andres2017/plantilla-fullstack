# Fábrica de builds (Claude Agent SDK) — guía rápida

Dashboard admin-only (`/builds` en el frontend) para editar una copia
aislada de la plantilla con un prompt en español, vía Claude Agent SDK.
Diseño completo en `docs/DECISIONS.md` (entrada "MISIÓN 14").

## 1. Activar el módulo

En `backend/.env`:

```bash
BUILDS_ENABLED=true
```

El resto de variables (`BUILDS_DAILY_BUDGET_USD`, `BUILDS_PER_BUILD_CAP_USD`,
`BUILDS_MAX_QUEUE_DEPTH`, `BUILDS_MAX_TURNS`, `BUILDS_TIMEOUT_SECONDS`,
`BUILDS_WORK_ROOT`, `BUILDS_TEMPLATE_ROOT`) ya están documentadas y con
default sensato en `backend/.env.example`.

## 2. Modo STUB vs modo AGENT

El modo se decide **al arrancar el proceso** según si `ANTHROPIC_API_KEY`
está presente en el entorno (`builds/config.py::agent_mode_enabled()`):

- **Sin la clave → STUB.** Simula el pipeline completo (working dir,
  "ediciones", zip) sin llamar a Anthropic. No gasta tokens. Sirve para
  probar UI, historial y descarga end-to-end.
- **Con la clave → AGENT SDK real.** Ejecuta el Claude Agent SDK de verdad
  sobre la copia aislada de la plantilla (sin Bash, tools limitadas a
  Read/Write/Edit/Glob/Grep, tope de costo por build).

Dos scripts en `backend/` arrancan cada modo con la config correcta:

```powershell
cd backend
.\start-backend-stub.ps1     # modo STUB, con --reload
.\start-backend-agent.ps1    # modo AGENT real, SIN --reload (via run_agent_server.py)
```

Si PowerShell bloquea la ejecución ("running scripts is disabled on this
system"), corré el script así en vez de cambiar la política global:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-backend-stub.ps1
```

## 3. Por qué el modo AGENT en Windows corre SIN `--reload`

`uvicorn --reload` en Windows fuerza `asyncio.SelectorEventLoop` en el
proceso donde realmente corre la app (`use_subprocess=True` cuando hay
`--reload` → `uvicorn/loops/asyncio.py` elige Selector en vez de Proactor).
`SelectorEventLoop` **no soporta subprocesos en Windows**, y el Agent SDK
necesita spawnear el CLI `claude` como subproceso para hacer cualquier
build real.

Sin este cuidado, el build falla con `error_code=BUILD_011_WINDOWS_EVENTLOOP`
(antes aparecía como `BUILD_009_WORKER_ERROR` con
`error_message="Failed to start Claude Code: "` vacío — mismo problema, sin
diagnóstico claro).

`start-backend-agent.ps1` NO confía únicamente en el flag `--loop none` de
uvicorn: arranca vía `run_agent_server.py`, que fuerza
`asyncio.WindowsProactorEventLoopPolicy()` **antes** de que uvicorn cree el
loop. Además, `agent_runner.py` ya no infiere la capacidad de spawnear
subprocesos por el nombre de la clase del loop (`isinstance` contra
`ProactorEventLoop` daba falsos negativos) — antes de cada build real prueba
un `asyncio.create_subprocess_exec` mínimo de verdad y solo falla con
`BUILD_011_WINDOWS_EVENTLOOP` si ese spawn realmente no funciona.

El modo STUB no lo sufre porque no spawnea ningún subproceso.

**Gotcha real encontrado en la práctica:** un proceso viejo de uvicorn con
`--reload` que haya quedado corriendo en el puerto 8001 (por ejemplo,
`--reload` en Windows arranca el proceso "reloader" + un hijo via
`multiprocessing`, y matar solo el proceso de la terminal a veces deja al
hijo escuchando el puerto) puede seguir atendiendo pedidos con
`SelectorEventLoop` **aunque arranques uno nuevo correctamente**. Si ves
`BUILD_011_WINDOWS_EVENTLOOP` justo después de correr
`start-backend-agent.ps1`, el script ahora te avisa si el puerto 8001 ya
tenía algo escuchando; si es así, cerralo primero:

```powershell
Get-NetTCPConnection -LocalPort 8001 | Select-Object OwningProcess
Stop-Process -Id <PID> -Force
```

Detalle completo de la causa original: `docs/DECISIONS.md`
(entrada 2026-07-23, "Fix: builds fallaban en Windows...").

## 4. Verificar que el loop es Proactor

Al arrancar con `start-backend-agent.ps1`, el log del worker imprime la
clase del event loop activo:

```
INFO - builds.worker - Worker de builds iniciado (modo AGENT SDK, event loop=ProactorEventLoop)
```

Si en vez de `ProactorEventLoop` aparece `SelectorEventLoop`, los builds
reales van a fallar con `BUILD_011_WINDOWS_EVENTLOOP` — revisá que no
estés usando `--reload` y que no haya un proceso viejo en el puerto 8001
(ver gotcha arriba). En modo STUB este log no incluye el loop porque no
es relevante (no spawnea subprocesos).

## 5. Verificar que el backend responde

```bash
# Login (guarda las cookies httpOnly de sesion)
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin123!"}'

# Presupuesto diario de builds (requiere admin autenticado)
curl -b cookies.txt http://localhost:8001/api/builds/budget
```

Respuesta esperada: `{"success":true,"data":{...},"error":null}`.

## 6. Tipos de entrega, agentes y modelos

La UI de `/builds` (rediseño "¿Qué vas a construir hoy?") deja elegir tres
cosas antes de escribir el prompt. Los tres viajan en `POST /builds/estimate`
y `POST /builds` como `template_type`, `agent` y `model`; se persisten en el
documento del build y `agent_runner.py` los usa para componer el system
prompt real y elegir el modelo. Catálogo fuente:
`frontend/src/features/builds/constants.js` (frontend) y
`backend/builds/models/build.py` (`Literal`s que validan el backend).

### Tipos de entrega (`template_type`)

| Valor | Label UI | Qué toca el agente |
|---|---|---|
| `full_stack` | App Full Stack | `backend/` y `frontend/src/features/` |
| `web_landing` | Página web / Landing | Solo `frontend/src/` (backend solo si el prompt lo pide explícito) |
| `mobile_apk` | App móvil (Capacitor/APK) | Config de Capacitor/`android/` + ajustes de frontend necesarios |
| `backend_only` | Solo API | Solo `backend/` (routers → services → repositories → models) |
| `custom` | Libre / avanzado | Sin restricción fija — sigue el alcance exacto del prompt |

Cada tipo inyecta un addendum distinto al system prompt del agente
(`agent_runner.py::_TEMPLATE_ADDENDA`) y ajusta el estimate: multiplica
`BUILDS_BASE_CONTEXT_TOKENS` por un factor (`build_service.py::
_TEMPLATE_CONTEXT_MULTIPLIER`) — `web_landing`/`backend_only` estiman menos
contexto (y por lo tanto menos costo) que `full_stack`/`mobile_apk`/`custom`.

### Agentes (`agent`)

| Valor | Label UI | Rol |
|---|---|---|
| `implementer` | Implementador | Implementa features sobre la plantilla (default, sin addendum extra) |
| `architect` | Arquitecto | Diseña estructura/contratos, escribe poco código |
| `reviewer` | Revisor | Revisa y refactoriza, NO agrega features nuevas |
| `mobile` | Móvil | Prioriza Capacitor/Android sobre el resto |
| `docs` | Documentación | Prioriza README/DECISIONS/comentarios |

Mismo system prompt base para todos — el addendum de agente
(`agent_runner.py::_AGENT_ADDENDA`) solo ajusta el foco, no reemplaza las
reglas obligatorias (capas estrictas, sin Bash, 4 estados en frontend, etc).

### Modelos (`model`)

Alias amigable de la UI → model id real, mapeado en `builds/config.py`
(`BUILDS_MODEL_MAP`, configurable por env sin tocar código):

| Alias | Label UI | Uso típico | Env var (id real) |
|---|---|---|---|
| `haiku` | Rápido / barato | Tareas chicas y acotadas | `BUILDS_MODEL_HAIKU` |
| `sonnet` | Equilibrado | Default para features normales | `BUILDS_MODEL_SONNET` |
| `opus` | Máxima calidad | Arquitectura compleja o refactors grandes | `BUILDS_MODEL_OPUS` |

El `model` también cambia la tarifa usada en el estimate
(`BUILDS_MODEL_PRICING` en `config.py`) — elegir `haiku` baja el costo
estimado, no solo cambia qué modelo corre.

### Recomendación automática

`frontend/src/features/builds/constants.js::recommendModel(templateType,
promptLength)` es una sugerencia visual (badge "Recomendado" + hint en
amarillo si elegís otra cosa) — **no bloquea** elegir otro modelo:

- `backend_only` + prompt corto (< 200 caracteres) → `haiku`
- Prompt muy largo (> 1500 caracteres, refactor grande) → `opus`
- Cualquier otro caso (incluido `mobile_apk`) → `sonnet`

## 7. Prompt de prueba sugerido por tipo de entrega

```
# full_stack
Agrega un módulo de facturación con lista, detalle y exportación a PDF,
con su endpoint FastAPI y su pantalla en React conectados.

# web_landing
Crea una landing de una sola página para el lanzamiento del producto: hero,
sección de features y formulario de contacto.

# mobile_apk
Ajusta la configuración de Capacitor para el splash screen y el ícono de
la app, y sube el versionCode.

# backend_only
Agrega un endpoint GET /api/items/stats que devuelva el total de items y
cuántos están activos. Solo backend: router → service → repository.

# custom
Describe exactamente qué archivos tocar y cuáles no, con el nivel de
detalle que necesites.
```

(Los mismos textos están precargados en la UI: botón "Usar un ejemplo" en
el composer, uno por tipo seleccionado.)

Flujo de prueba: elegí tipo + agente + modelo desde la UI, calculá el
costo, confirmá, seguí el progreso (SSE) hasta `completed`, y descargá el
zip. Si el build termina en `failed`, la tabla de historial
(`BuildHistoryTable.jsx`) muestra un tooltip con `error_code` y
`error_message` sobre el badge de estado — no hace falta ir a Mongo para
ver la causa.
