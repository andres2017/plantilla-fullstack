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
.\start-backend-agent.ps1    # modo AGENT real, SIN --reload
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
diagnóstico claro). `start-backend-agent.ps1` ya arranca con `--loop none`
para evitarlo. Detalle completo de la causa: `docs/DECISIONS.md`
(entrada 2026-07-23, "Fix: builds fallaban en Windows...").

El modo STUB no lo sufre porque no spawnea ningún subproceso.

## 4. Verificar que el backend responde

```bash
# Login (guarda las cookies httpOnly de sesion)
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin123!"}'

# Presupuesto diario de builds (requiere admin autenticado)
curl -b cookies.txt http://localhost:8001/api/builds/budget
```

Respuesta esperada: `{"success":true,"data":{...},"error":null}`.

## 5. Prompt de prueba sugerido

Backend-only, acotado, fácil de verificar a simple vista en el zip:

```
Agrega un endpoint GET /api/items/stats que devuelva el total de items y
cuántos están activos.
Solo backend: router → service → repository.
No toques el frontend ni auth.
```

Flujo de prueba: crear el build desde la UI (o `POST /api/builds`), seguir
el progreso (SSE) hasta `completed`, y descargar el zip. Si el build termina
en `failed`, la tabla de historial (`BuildHistoryTable.jsx`) muestra un
tooltip con `error_code` y `error_message` sobre el badge de estado — no
hace falta ir a Mongo para ver la causa.
