# CI/CD

## Qué corre en cada push y pull request

Al hacer `push` a cualquier rama o abrir/actualizar un pull request, GitHub Actions
ejecuta `.github/workflows/ci.yml` con 3 jobs en paralelo:

| Job | Qué hace | Dónde |
|---|---|---|
| `backend` | Instala dependencias, corre `ruff check .` (lint), levanta el backend real contra un MongoDB de servicio y corre la suite completa de `pytest` (16 tests: auth, RBAC, items) | `backend/` |
| `frontend` | Instala dependencias con `yarn` y corre `yarn build` (build de producción con `craco`) | `frontend/` |
| `audit-deps` | Corre `pip-audit` (backend) y `yarn audit` (frontend), pero **solo falla si hay vulnerabilidades HIGH o CRITICAL** | ambos |

Si cualquier job falla, el pull request se marca en rojo y no debería mergearse
(aunque GitHub no lo bloquea automáticamente salvo que actives "branch
protection rules" en la configuración del repo, que no está incluida aquí).

### Por qué `audit-deps` no usa el exit code nativo de las herramientas

- **`pip-audit`** no reporta severidad en su propio JSON (solo IDs de
  vulnerabilidad). El job consulta la API pública de [OSV.dev](https://osv.dev)
  por cada ID encontrado y calcula la severidad real (etiqueta de GHSA o score
  CVSS con la librería `cvss`). Ver `backend/scripts/check_pip_audit_severity.py`.
- **`yarn audit --level high`** no filtra el exit code como parece indicar su
  documentación: en Yarn Classic (v1) el exit code es un bitmask de **todas**
  las severidades encontradas, incluyendo `low`/`moderate`. El job en cambio
  lee el JSON de `yarn audit` y solo falla si `high > 0 || critical > 0`. Ver
  `frontend/scripts/check-audit-severity.js`.

## Cómo leer un fallo del pipeline

1. Entra a la pestaña **Actions** del repo en GitHub y abre el run en rojo.
2. Cada job tiene sus pasos (`steps`) — el que tiene la ❌ es el que falló, el
   log de ese paso específico casi siempre tiene el error real.
3. Fallos comunes:
   - **`backend` falla en "Lint (ruff)"**: hay un error de estilo. Corre
     `ruff check .` localmente dentro de `backend/` (con el venv activado) para
     reproducirlo.
   - **`backend` falla en "Levantar backend"**: el servidor no respondió a
     `/api/health` en 30 intentos de 1s. Revisa el log de `uvicorn.log` que se
     imprime automáticamente (paso "Logs del backend si algo falló") — casi
     siempre es un error al conectar a Mongo, una variable de entorno faltante,
     o (si `PAYMENTS_ENABLED=true`) credenciales de Wompi incompletas (ver
     `docs/PAGOS.md` — el módulo de pagos falla rápido a propósito si falta algo).
   - **`backend` falla en "Tests (pytest)"**: algún test real falló contra el
     servidor. El log de pytest indica cuál. **No** modifiques
     `backend/pytest.ini` (`addopts = -n 2 --dist loadscope`) para "arreglarlo" —
     ese valor es intencional (paraleliza por clase/módulo porque los tests
     comparten un solo backend con estado secuencial).
   - **`frontend` falla en "Build"**: error de compilación real (JSX, import
     roto, etc.). Corre `yarn build` localmente en `frontend/`.
   - **`audit-deps` falla**: hay una dependencia con CVE HIGH/CRITICAL. El log
     imprime el paquete, la versión, el ID de la vulnerabilidad y la versión
     que la arregla. Actualiza esa dependencia (o, si no es posible sin romper
     compatibilidad, es una decisión para `auditor-seguridad`, no un
     workaround del pipeline).

## Vista previa por rama (Vercel + Render) — patrón recomendado, sin deploy propio

Esta plantilla **no tiene su propio deploy real** (es un molde, no una app
viva) — `render.yaml`/`frontend/vercel.json` quedan como configuración lista
para copiar, con los valores sensibles en placeholder. Cada proyecto que nazca
de acá conecta sus propios proveedores al desplegar de verdad.

**Por qué Vercel + Render y no Railway:** de las opciones evaluadas, Railway
tiene mejor DX pero ya no es gratis de forma indefinida (trial de $5 por 30
días, luego mínimo $5/mes). Render Hobby es gratis indefinido con "PR
Previews" nativas (se duerme tras 15 min sin uso, cold start 30-60s). Vercel
Hobby es gratis con preview automático ilimitado por rama, sin config
adicional. Ninguno de los dos incluye MongoDB nativo — hace falta un cluster
gratis de MongoDB Atlas (M0) aparte.

- **Frontend → Vercel.** Cada push a una rama o PR genera una URL de preview
  automática (`https://<proyecto>-git-<rama>-<usuario>.vercel.app`), nativo de
  Vercel, sin workflow propio. Configuración en `frontend/vercel.json`.
  **Setup único:** en vercel.com, importar el repo y fijar *Root Directory* =
  `frontend` (es un monorepo).
- **Backend → Render.** `render.yaml` en la raíz define el servicio con
  `previews.generation: automatic`: cada PR levanta una copia efímera del
  backend, se destruye sola al cerrar/mergear el PR. **Setup único:** en
  render.com, "New Blueprint" apuntando a este repo (si el repo tiene más de
  una rama con `render.yaml`, apuntar el Blueprint a la rama por defecto real
  del proyecto, no asumir `main` a ciegas).

### Secretos del proveedor de deploy (nunca en el repo)

`render.yaml` marca con `sync: false` las variables que Render debe pedir a
mano (nunca se leen del repo ni se commitean):

| Variable | De dónde sale |
|---|---|
| `MONGO_URL` | Connection string de un cluster gratis de MongoDB Atlas (M0). Render no tiene Mongo nativo. |
| `CORS_ORIGINS` | URL de producción del frontend, si la hay. |
| `ADMIN_PASSWORD` / `USER_PASSWORD` | Contraseñas de las cuentas semilla — no reutilizar las de `.env` local. |

`JWT_SECRET` usa `generateValue: true`: Render genera un valor aleatorio
distinto por servicio/preview, no hace falta configurarlo a mano.

En Vercel, cualquier variable de entorno del frontend (si se agrega alguna a
futuro) se configura en el dashboard del proyecto → *Settings* →
*Environment Variables*, nunca en `vercel.json` ni en el repo.

### `CORS_ORIGIN_REGEX`: anclar siempre, nunca un comodín

`render.yaml` trae `CORS_ORIGIN_REGEX` **comentado**, a propósito — esta
plantilla no tiene un dominio real al que anclarlo. Cuando un proyecto nazca
de acá y despliegue de verdad, hay que descomentarlo y fijarlo al dominio
real de Vercel de ESE proyecto, nunca `'https://.*\.vercel\.app'` a secas
(eso acepta el subdominio de *cualquier* proyecto de Vercel de *cualquier*
persona, y combinado con `COOKIE_SAMESITE=none` abre CSRF real).

Ejemplo real y verificado en producción (de `code_key`, una app derivada de
esta plantilla — mostrado acá solo como referencia de formato, **no copiar el
dominio**, cada proyecto tiene el suyo):
```
'^https://code-key-seven\.vercel\.app$|^https://code-key-[a-zA-Z0-9-]+-andres2017s-projects\.vercel\.app$'
```
Patrón: producción fija (`^https://<proyecto>\.vercel\.app$`) + previews del
mismo proyecto/team (`^https://<proyecto>-[a-zA-Z0-9-]+-<team>\.vercel\.app$`),
unidos con `|`. Verificar con casos de ataque (prefijo/sufijo/otro proyecto)
antes de dar por bueno el regex — ver `docs/DECISIONS.md` de `code_key` para
el detalle de esa verificación.

### Limitación conocida: el frontend no descubre solo la URL del backend de preview

Vercel y Render son proveedores separados sin integración cruzada. CRA
"hornea" `REACT_APP_BACKEND_URL` en build-time, así que el build de Vercel no
sabe automáticamente qué URL le tocó al backend de preview en Render para esa
misma rama. **Mientras no se automatice esto:**

1. Abre el PR → espera a que Render publique la URL del preview del backend
   (aparece como status check en el PR).
2. En Vercel, ve al deployment de preview de esa rama → *Settings* →
   *Environment Variables* → agrega `REACT_APP_BACKEND_URL` con esa URL →
   *Redeploy*.

Automatizar esto (un Action que lea la URL de Render vía su API y la empuje a
Vercel vía la suya) es posible pero queda fuera de "la opción más simple y
gratuita" — es una mejora propuesta, no implementada. Ver `docs/DECISIONS.md`.
