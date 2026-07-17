# Auth Testing Playbook

Step 1: MongoDB Verification
```
mongosh
use <DB_NAME>
db.users.find({role: "admin"}).pretty()
db.users.findOne({role: "admin"}, {password_hash: 1})
```
Verify: bcrypt hash starts with `$2b$`, indexes exist on users.email (unique), login_attempts.identifier, refresh_tokens.expires_at (TTL).

Step 2: API Testing
```
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"Admin123!"}'
cat cookies.txt
curl -b cookies.txt http://localhost:8001/api/auth/me
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8001/api/auth/refresh
curl -b cookies.txt http://localhost:8001/api/auth/me
```

Login should return `{success: true, data: {user...}}` and set `access_token` + `refresh_token` cookies. `/me` should return the same user. `/refresh` rotates the refresh token (reusing an old refresh token must return 401).

RBAC: login as usuario@example.com / Usuario123! and attempt POST /api/items → must return 403 with `{success: false, error: "Requiere rol de administrador"}`.
