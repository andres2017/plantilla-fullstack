# PRD — {APP_NAME}

> Plantilla vacía. Pide al subagente `arquitecto` que la complete cuando
> definas la primera funcionalidad real (ver docs/COMO-USAR-PLANTILLA.md).

## Problema original
_(Qué problema resuelve la app, para quién, en una o dos frases.)_

## Personas
_(Roles y qué necesita lograr cada uno.)_

## Requisitos core
- Backend FastAPI en capas: routers/services/repositories/models + core (config, db, seguridad, responses).
- Frontend React + Tailwind con arquitectura por features, layout navbar + sidebar.
- Auth completa: registro, login, JWT access (15 min) + refresh (7 días) con rotación real, bcrypt, RBAC admin/usuario, cookies httpOnly, lockout 5 intentos/15 min por email.
- CRUD de referencia: `items` (ver backend/routers/items.py y frontend/src/features/items/).

## Backlog priorizado
_(P0/P1/P2 — qué se construye primero y por qué.)_

## Notas técnicas
- Envelope de error global vía exception handlers (HTTPException y 422).
- Tests backend: `backend/tests/backend_test.py` (`pytest backend/tests/backend_test.py -v`).
- Playbook auth para testers: `auth_testing.md`.
- Decisiones de arquitectura: `docs/DECISIONS.md`.
