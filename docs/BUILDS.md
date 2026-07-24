# Fábrica Cyberandres — guía v2.1

Escuela + taller + entrega. El usuario elige un tipo de producto, ve el **mapa de pasos**, puede **aprender** o **construir**, y descarga un zip.

## Idioma

Selector **Español | English** en `/builds`. Preferencia en `localStorage` (`fabrica_locale`) y campo `locale` en estimate/create.

## Blueprints

- Fuente: `shared/blueprints/*.json` (textos bilingües `{ "es", "en" }`)
- API:
  - `GET /api/blueprints?locale=es|en`
  - `GET /api/blueprints/{id}?locale=`
  - `GET /api/blueprints/{id}/progress`

Progreso = builds del admin con `blueprint_step_id` (no hay tabla checklist).

## Crear build (campos opcionales)

```json
{
  "prompt": "...",
  "template_type": "full_stack",
  "blueprint_step_id": "auth",
  "mode": "learn",
  "agent": "implementer",
  "model": "haiku",
  "locale": "es"
}
```

`mode=learn` reduce el estimado. `has_zip` es real (`Path.is_file()`).

## Local (plantilla)

1. Mongo / Atlas  
2. `backend/.env` con `BUILDS_ENABLED=true`  
3. Backend: `start-backend-stub.ps1` o `start-backend-agent.ps1` (Windows Agent sin `--reload`)  
4. Frontend: `npm start`  

## Publicar (recomendado por tipo)

| Tipo | Stack sugerido |
|------|----------------|
| full_stack | Atlas + Render/Railway (API) + Vercel/Netlify (front) |
| web_landing | Vercel / Netlify |
| backend_api | Render/Railway + Atlas |
| mobile_apk | API publicada + Capacitor APK |

## Windows + Agent SDK

Usar `start-backend-agent.ps1` (Proactor). No dejes procesos `--reload` huérfanos en el puerto 8001.

## Seguridad

- No subir `.env` ni zips de prueba  
- Agent sin Bash  
- Literals Pydantic en template_type/agent/model/locale  
