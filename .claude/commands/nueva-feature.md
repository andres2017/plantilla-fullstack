---
description: Flujo completo para una funcionalidad nueva — arquitecto diseña y espera tu aprobación, luego implementación, QA visual y auditoría de seguridad.
argument-hint: <descripción de la funcionalidad>
---

Vas a orquestar el flujo de FASE 1 a FASE 5 de `CLAUDE.md` para esta funcionalidad nueva:

> $ARGUMENTS

## Paso 1 — Diseño (compuerta bloqueante)

Invoca al subagente `arquitecto` (Agent tool, `subagent_type: "arquitecto"`) con el brief de arriba y el contexto de este repo: arquitectura en capas del backend (`backend/routers/items.py` → `services/item_service.py` → `repositories/item_repository.py` → `models/item.py` como plantilla a duplicar) y arquitectura por features del frontend (`frontend/src/features/items/` como plantilla). Debe entregar modelos de datos, contratos exactos de request/response, tabla de endpoints (método, ruta, auth requerida), mapa de pantallas y riesgos técnicos, y registrar la decisión en `docs/DECISIONS.md`.

Presenta el diseño completo al usuario y **DETENTE AHÍ**. No implementes nada todavía — esperá aprobación explícita del usuario en su próximo mensaje. Si pide cambios, volvé a invocar a `arquitecto` con ese feedback antes de continuar.

## Paso 2 — Implementación (solo después de la aprobación)

En el mismo mensaje, dos llamadas al Agent tool en paralelo:
- `backend-senior`: implementa siguiendo el diseño aprobado. Cada endpoint con pruebas ejecutadas (200/401/403/404/422) y evidencia mostrada, no solo afirmada.
- `frontend-senior`: implementa la(s) pantalla(s) con los 4 estados obligatorios (cargando/vacío/error/éxito), consumiendo únicamente el contrato de API que definió el arquitecto — nunca datos quemados.

## Paso 3 — QA

Invoca a `qa-lead`: pruebas de API con curl/requests + flujo completo en navegador real (Playwright MCP), con capturas guardadas en `test_reports/qa-visual/`. Tiene que cerrar con veredicto explícito APROBADO/RECHAZADO. Si RECHAZADO, volvé a `backend-senior`/`frontend-senior` con la lista de bugs antes de seguir.

## Paso 4 — Seguridad

Invoca a `auditor-seguridad` sobre el diff de esta funcionalidad (checklist OWASP completo). CRÍTICO o ALTO abierto = veto: no se puede dar por lista hasta corregirlo y volver a auditar.

## Paso 5 — Resumen final

Mostrale al usuario: qué se construyó (archivos tocados), evidencia de `qa-lead` (capturas + resultados), veredicto de `auditor-seguridad`, y deuda técnica pendiente si la hay. No hagas commit salvo que el usuario lo pida explícitamente en este mismo hilo.
