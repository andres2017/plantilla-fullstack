# Credenciales de prueba

Usuarios semilla (se crean automáticamente al arrancar el backend, según backend/.env):

| Rol | Email | Contraseña |
|---|---|---|
| admin | admin@example.com | Admin123! |
| usuario | usuario@example.com | Usuario123! |

## Endpoints de auth
- POST /api/auth/register — { email, name, password }
- POST /api/auth/login — { email, password } (cookies httpOnly: access_token + refresh_token)
- POST /api/auth/refresh — rota refresh token
- POST /api/auth/logout
- GET /api/auth/me

## Notas
- Formato de respuesta uniforme: { "success", "data", "error" }
- Escritura en /api/items requiere rol admin; lectura requiere usuario autenticado.
- Bloqueo de login: 5 intentos fallidos → 15 min.
