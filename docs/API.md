# API

Base URL: `{BACKEND_URL}/api`

## Formato de respuesta estándar

Toda respuesta (2xx, 4xx, 5xx) sigue este envelope:

```json
{ "success": true,  "data": <payload>, "error": null }
{ "success": false, "data": null,      "error": "Mensaje legible" }
```

Los listados paginados devuelven en `data`:

```json
{
  "items": [ ... ],
  "pagination": { "page": 1, "limit": 10, "total": 42, "total_pages": 5 }
}
```

## Autenticación

Los tokens viajan en cookies httpOnly (`access_token` 15 min, `refresh_token` 7 días con rotación). También se acepta `Authorization: Bearer <access_token>`.

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| POST | `/auth/register` | — | Registro. Body: `{ "email", "name", "password" }`. Crea usuario con rol `usuario` y setea cookies. |
| POST | `/auth/login` | — | Login. Body: `{ "email", "password" }`. Bloqueo de 15 min tras 5 intentos fallidos. |
| POST | `/auth/refresh` | cookie refresh | Rota el refresh token (el anterior queda invalidado) y emite nuevo access token. |
| POST | `/auth/logout` | cookie refresh | Revoca el refresh token y borra cookies. |
| GET | `/auth/me` | access | Devuelve el usuario autenticado: `{ id, email, name, role }`. |

## Items (entidad de referencia)

CRUD de ejemplo. Duplica `routers/items.py` → `services/item_service.py` → `repositories/item_repository.py` → `models/item.py` para cada entidad nueva de tu dominio.

Lectura: cualquier usuario autenticado. Escritura: solo rol `admin` (403 en caso contrario).

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| POST | `/items` | admin | Crear item. Body: `{ "name", "description"?, "active"? }`. |
| GET | `/items` | usuario | Listado paginado. Query: `page` (def. 1), `limit` (def. 10, máx. 100), `active` (`true`\|`false`, opcional). |
| GET | `/items/{id}` | usuario | Detalle de un item. 404 si no existe. |
| PATCH | `/items/{id}` | admin | Actualizar. Body (parcial): `{ "name"?, "description"?, "active"? }`. |
| DELETE | `/items/{id}` | admin | Eliminar. Devuelve `{ "deleted": true }`. |

### Objeto Item

```json
{
  "id": "665f...",
  "name": "Primer item",
  "description": "Detalle breve",
  "active": true,
  "created_by": "<user_id>",
  "created_at": "2026-06-10T12:00:00Z"
}
```

## Utilidades

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | — | Health check del servicio. |

## Códigos de error habituales

| HTTP | Motivo |
|---|---|
| 401 | Sin token, token expirado/inválido o credenciales incorrectas |
| 403 | Autenticado pero sin rol `admin` |
| 404 | Recurso no encontrado |
| 409 | Conflicto (ej. email duplicado) |
| 422 | Error de validación (mensajes concatenados en `error`) |
| 429 | Bloqueo temporal por intentos fallidos de login |
