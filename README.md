# Plantilla Full-Stack

Base reutilizable para arrancar un proyecto nuevo: autenticación completa
(JWT + refresh con rotación, RBAC admin/usuario) y una entidad de ejemplo
(`items`) que muestra el patrón de capas de punta a punta — backend y
frontend. El resto del negocio se construye a partir de aquí.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI (Python 3.11) en capas: `routers/ services/ repositories/ models/` |
| Base de datos | MongoDB (driver async Motor) |
| Frontend | React 19 + Tailwind CSS + Shadcn UI, arquitectura por features |
| Auth | JWT access (15 min) + refresh con rotación (7 días), cookies httpOnly, bcrypt, RBAC (admin/usuario) |

## Estructura

```
/backend
  core/           # config, conexión Mongo, seguridad (JWT/bcrypt/RBAC), formato de respuesta, core/time.py (helper as_utc)
  models/         # Pydantic: user, item
  repositories/   # acceso a datos (MongoDB)
  services/       # lógica de negocio
  routers/        # endpoints HTTP (/api/*)
  server.py       # app FastAPI, CORS, seeds, manejadores de error
/frontend
  src/
    config.js              # APP_NAME (desde REACT_APP_APP_NAME)
    lib/api.js              # cliente axios (cookies + auto-refresh de token)
    features/auth/          # contexto, login, registro, ruta protegida
    features/items/         # CRUD de referencia (4 estados: cargando/vacío/error/éxito)
    components/layout/      # AppLayout (navbar + sidebar)
    components/ui/          # Shadcn UI
/docs
  API.md                    # documentación de endpoints
  DECISIONS.md               # decisiones de arquitectura
  COMO-USAR-PLANTILLA.md    # flujo para arrancar un proyecto nuevo desde aquí
/CLAUDE.md         # constitución del equipo de ingeniería (subagentes en .claude/agents/)
```

## Cómo bautizar un proyecto nuevo (3 pasos)

1. **Nombre:** define `APP_NAME` (backend) y `REACT_APP_APP_NAME` (frontend) en
   los `.env` — se usan en el título de la API, el sidebar, las pantallas de
   auth y el `<title>` del navegador. No hay que tocar código para renombrar.
2. **`.env`:** copia `backend/.env.example` → `backend/.env` y
   `frontend/.env.example` → `frontend/.env`, ajusta `MONGO_URL`/`DB_NAME` y
   genera un `JWT_SECRET` propio (`openssl rand -hex 32`).
3. **Primer commit:** una vez renombrado, haz el primer commit del proyecto
   ya bautizado (ver "Instalación local" abajo para levantar y confirmar que
   arranca antes de commitear).

## Instalación local

### Requisitos
- Python 3.11+, Node 18+, Yarn 1.x, MongoDB corriendo en local (o Atlas).

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # editar valores (ver tabla abajo)
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

API disponible en `http://localhost:8001/api` (health check: `GET /api/health`).
Al arrancar se crean automáticamente los índices de MongoDB y los usuarios semilla (admin y usuario).

### 2. Frontend

```bash
cd frontend
yarn install
cp .env.example .env            # apuntar REACT_APP_BACKEND_URL al backend
yarn start
```

App disponible en `http://localhost:3000`.

## Variables de entorno

### backend/.env

| Variable | Descripción | Ejemplo |
|---|---|---|
| `APP_NAME` | Nombre visible de la app (título API, logs) | `MiApp` |
| `MONGO_URL` | Cadena de conexión a MongoDB | `mongodb://localhost:27017` |
| `DB_NAME` | Nombre de la base de datos | `miapp_db` |
| `CORS_ORIGINS` | Orígenes permitidos (separados por coma) | `http://localhost:3000` |
| `JWT_SECRET` | Secreto para firmar JWT (`openssl rand -hex 32`) | `8f4b2e...` |
| `ADMIN_EMAIL` | Email del admin semilla | `admin@example.com` |
| `ADMIN_PASSWORD` | Contraseña del admin semilla | `Admin123!` |
| `USER_EMAIL` | Email del usuario semilla | `usuario@example.com` |
| `USER_PASSWORD` | Contraseña del usuario semilla | `Usuario123!` |

### frontend/.env

| Variable | Descripción | Ejemplo |
|---|---|---|
| `REACT_APP_APP_NAME` | Nombre visible de la app (sidebar, auth, `<title>`) | `MiApp` |
| `REACT_APP_BACKEND_URL` | URL pública del backend, sin barra final | `http://localhost:8001` |

## Credenciales de prueba

| Rol | Email | Contraseña |
|---|---|---|
| Admin | `admin@example.com` | `Admin123!` |
| Usuario | `usuario@example.com` | `Usuario123!` |

## Formato de respuesta de la API

Todas las respuestas (éxito y error) siguen el formato uniforme:

```json
{ "success": true,  "data": { ... }, "error": null }
{ "success": false, "data": null,   "error": "Mensaje de error" }
```

Ver [docs/API.md](docs/API.md) para el detalle de endpoints.

## Cómo agregar tu primera funcionalidad real

Ver [docs/COMO-USAR-PLANTILLA.md](docs/COMO-USAR-PLANTILLA.md) — resume el
flujo clonar → renombrar → correr → pedirle al subagente `arquitecto`
(`.claude/agents/arquitecto.md`) el diseño de la primera entidad, usando
`items` como plantilla a duplicar.
