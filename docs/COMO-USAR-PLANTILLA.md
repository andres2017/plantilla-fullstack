# Cómo usar esta plantilla

Flujo recomendado para arrancar un proyecto nuevo a partir de esta base.

## 1. Clonar

```bash
git clone <tu-fork-o-copia-de-la-plantilla> mi-proyecto
cd mi-proyecto
```

(Si venís de copiar la carpeta a mano en vez de clonar, corré `git init` —
ver la sección de git en el README si necesitás los pasos exactos.)

## 2. Renombrar

Seguí los "3 pasos para bautizar un proyecto nuevo" del README:
`APP_NAME`/`REACT_APP_APP_NAME` en los `.env`, revisar `MONGO_URL`/`DB_NAME`,
generar un `JWT_SECRET` propio.

## 3. Correr

```bash
# backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# frontend (otra terminal)
cd frontend && yarn install && cp .env.example .env && yarn start
```

Confirmá que `GET /api/health` responde y que podés hacer login con las
credenciales semilla (ver README) en `http://localhost:3000`.

## 4. Pedirle al arquitecto el diseño de la primera funcionalidad

Este template viene con `CLAUDE.md` y 7 subagentes en `.claude/agents/`
(arquitecto, backend-senior, frontend-senior, auditor-seguridad, dba,
qa-lead, devops-release) que ya conocen las convenciones del proyecto:
capas estrictas en el backend, arquitectura por features en el frontend,
envelope `{success, data, error}`, paginación, RBAC.

Antes de escribir código para tu primera entidad de negocio real, pedile al
subagente `arquitecto` que la diseñe: modelos de datos, contratos de API,
mapa de pantallas y riesgos. Con ese diseño aprobado, `backend-senior` y
`frontend-senior` implementan siguiendo el mismo patrón que ya ves en
`items` (`backend/routers/items.py` → `services/item_service.py` →
`repositories/item_repository.py` → `models/item.py`, y
`frontend/src/features/items/`) — duplicá esa carpeta/esos archivos como
punto de partida en vez de empezar en blanco.

`qa-lead` valida con evidencia antes de marcar algo como "listo", y
`auditor-seguridad` audita cualquier cambio en auth, endpoints o
formularios. Ver las reglas de delegación y de bloqueo en `CLAUDE.md`.
