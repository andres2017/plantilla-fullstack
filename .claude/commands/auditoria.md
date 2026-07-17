---
description: Auditoría de seguridad completa (checklist OWASP) sobre el estado actual del proyecto, con hallazgos por severidad.
---

Invoca al subagente `auditor-seguridad` (Agent tool, `subagent_type: "auditor-seguridad"`) para que ejecute su checklist completo (ver `.claude/agents/auditor-seguridad.md`) sobre el estado **actual de todo el proyecto** — no solo el último diff:

- Validación y sanitización de toda entrada en backend
- Anti-inyección NoSQL/SQL y XSS (escape de salida)
- Rate limiting en login/registro/endpoints de escritura, bloqueo tras intentos fallidos
- CORS restringido a dominios explícitos
- Headers de seguridad (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)
- Secretos solo en `.env`, `.gitignore` correcto, grep de credenciales hardcodeadas
- IDs secuenciales expuestos vs UUIDs/ObjectId
- Anti-IDOR: cada endpoint valida propiedad del recurso, no solo autenticación
- Logs sin contraseñas/tokens/datos sensibles
- Dependencias con CVEs críticos conocidos

El reporte debe listar cada hallazgo como: **severidad** (CRÍTICO/ALTO/MEDIO/BAJO) — `archivo:línea` — explicación del ataque posible — corrección concreta propuesta. Cerrar con veredicto explícito: **VETO** (si hay CRÍTICO/ALTO sin corregir) o **APROBADO**.

Mostrame el reporte completo, sin resumir ni omitir hallazgos.
