---
description: Checklist de pre-release — tests completos, auditoría sin vetos, docs al día, y commit final.
---

Ejecutá la verificación de pre-release (rol `devops-release` de `CLAUDE.md`). Marcá cada ítem explícitamente ✅/❌ a medida que lo vas verificando — no todo junto al final:

1. **Tests backend:** correr `pytest backend/tests/backend_test.py -v` contra el servidor real (levantalo primero si no está arriba). ✅ solo si todos pasan; si algo falla, quedás en ❌ y no seguís.
2. **Auditoría de seguridad:** invocar a `auditor-seguridad` con el mismo checklist de `/auditoria`. ✅ solo si no hay veto (sin CRÍTICO/ALTO abiertos).
3. **QA de los flujos críticos:** confirmar veredicto APROBADO de `qa-lead` para los 3 flujos más importantes de punta a punta (o correrlo si no hay evidencia reciente).
4. **README.md al día:** comparar contra el estado real del código (endpoints en `docs/API.md`, variables de entorno, estructura de carpetas) y corregir lo que esté desactualizado.
5. **`.env.example` al día:** toda variable que el código lea con `os.environ[...]` (backend) o `process.env....`/`REACT_APP_*` (frontend) tiene que estar documentada ahí con un valor de ejemplo — nunca uno real.
6. **Sin secretos ni `.env` reales en el árbol a commitear:** `git status` + confirmar que `.gitignore` los cubre.

Si TODOS los ítems quedan en ✅: preparar el mensaje de commit final (Conventional Commits, describiendo el release) y pedir confirmación explícita antes de correr `git commit`. Si el usuario ya dio luz verde de antemano en este mismo hilo, hacelo directamente — pero nunca hagas `git push` sin una confirmación aparte.

Si algún ítem queda en ❌: NO commitear. Reportar exactamente qué falta y detenerte ahí.
