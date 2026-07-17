---
description: qa-lead prueba un flujo específico de punta a punta en navegador real, con capturas y veredicto.
argument-hint: <flujo a probar, ej. "login", "registro", "CRUD de items">
---

Invoca al subagente `qa-lead` (Agent tool, `subagent_type: "qa-lead"`) para probar de punta a punta este flujo:

> $ARGUMENTS

Debe: diseñar el plan de prueba antes de ejecutar (caso feliz + casos límite relevantes a este flujo puntual); confirmar que el stack esté arriba (backend + frontend — si no, levantarlos siguiendo el README) antes de probar; usar el navegador real vía Playwright MCP para los pasos de UI; guardar una captura por paso relevante en `test_reports/qa-visual/` con nombre descriptivo (`AAAA-MM-DD_<paso>.png`); documentar comando/acción ejecutada → resultado esperado vs obtenido para cada paso.

Cerrar siempre con veredicto explícito: **APROBADO** o **RECHAZADO** + lista de bloqueantes si aplica. Mostrame el reporte completo con las rutas de las capturas.
