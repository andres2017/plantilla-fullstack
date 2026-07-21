# Módulo de pagos (opcional) — Wompi

Módulo de pagos **desacoplado y opcional**: si tu proyecto no cobra dinero,
no lo actives y no cambia nada (cero rutas nuevas, cero índices nuevos,
cero cliente HTTP instanciado). Vive completo en `backend/payments/` como
un subpaquete que podés copiar tal cual a otro proyecto con esta misma
arquitectura de capas.

Ver la decisión de diseño completa (comparación de pasarelas, por qué
Wompi, mecanismo exacto de idempotencia/validación de monto) en
`docs/DECISIONS.md`.

## Activar el módulo en un proyecto nuevo

1. **Conseguir credenciales de Wompi** (gratis, sin KYC para sandbox):
   - Creá una cuenta en [comercios.wompi.co](https://comercios.wompi.co) con
     solo un correo.
   - En el panel: *Desarrolladores* → copiá `Public Key` y `Private Key`
     del ambiente **sandbox**.
   - En la misma sección: *Eventos* → generá/copiá el `Secreto de eventos`
     (`WOMPI_EVENTS_SECRET`) — es **distinto** de las llaves de arriba.
   - En *Llaves*: copiá el `Secreto de integridad` (`WOMPI_INTEGRITY_SECRET`)
     — también distinto de las otras tres.

2. **Configurar `backend/.env`**:
   ```bash
   PAYMENTS_ENABLED=true
   PAYMENT_PROVIDER=wompi
   PAYMENTS_MIN_AMOUNT_CENTS=100000
   PAYMENTS_MAX_AMOUNT_CENTS=500000000
   PAYMENTS_SUPPORTED_CURRENCIES=COP
   WOMPI_ENV=sandbox
   WOMPI_PUBLIC_KEY=pub_test_...
   WOMPI_PRIVATE_KEY=prv_test_...
   WOMPI_EVENTS_SECRET=...
   WOMPI_INTEGRITY_SECRET=...
   ```
   Con `PAYMENTS_ENABLED=false` o ausente, el resto de estas variables no
   se validan y no hace falta tenerlas — la app arranca exactamente igual
   que sin el módulo.

3. **Reiniciar el backend.** Vas a ver en el log que se crean los índices
   de `payments`/`payment_events`, y `GET /api/payments` (antes `404`)
   ahora responde (requiere sesión).

4. **Configurar la URL del webhook en el panel de Wompi**: *Desarrolladores*
   → *Eventos* → URL del webhook:
   ```
   https://tu-backend.com/api/payments/webhook/wompi
   ```
   En local, para probar webhooks reales de principio a fin, necesitás
   exponer tu backend con algo como [ngrok](https://ngrok.com/) (Wompi
   necesita poder pegarle a una URL pública, no a `localhost`).

## Probar en sandbox

Con `WOMPI_ENV=sandbox`, cualquier pago que hagas en el checkout de Wompi
es simulado (no se cobra dinero real). Wompi documenta tarjetas de prueba
que fuerzan cada resultado (aprobada, declinada, error) — revisá su
documentación de "Tarjetas de prueba" vigente al momento de integrar, ese
detalle cambia con el tiempo y no se fija acá para no quedar desactualizado.

Flujo de prueba de punta a punta:
1. `POST /api/payments` con una descripción y un monto → te devuelve
   `checkout.checkout_url`.
2. Abrí esa URL en el navegador, completá el pago con una tarjeta de
   prueba.
3. Wompi redirige de vuelta y (por separado, de forma asíncrona) manda el
   webhook a tu backend.
4. `GET /api/payments/{reference}` — el estado pasa de `pendiente` a
   `pagado` (o `fallido`) cuando el webhook se procesa. **El frontend debe
   hacer polling a este endpoint, nunca confiar en los parámetros de la
   URL de retorno** (son solo una pista de UX, trivialmente falsificables
   — ver `docs/DECISIONS.md`).

## Cómo se integra en tu app anfitriona

El módulo no conoce tus entidades de negocio (no sabe qué es un "plan" o
un "pedido"). El punto de extensión es `metadata` (dict libre) en
`POST /payments`:

```json
{
  "amount_cents": 5000000,
  "currency": "COP",
  "description": "Suscripción plan Pro - 1 mes",
  "metadata": { "plan_id": "pro-mensual", "pedido_id": "abc123" }
}
```

**El monto SIEMPRE lo calcula tu backend anfitrión** antes de llamar a
`POST /payments` (ej. mirando tu catálogo/plan real) — este módulo no
implementa un modo de "monto libre" elegido por el cliente. `metadata` es
lo que después leés vos para saber a qué activar/desbloquear cuando el
pago se confirma (por ahora eso es responsabilidad de tu propio código,
consultando `GET /payments/{reference}` o directamente la colección
`payments`; no hay un sistema de webhooks/hooks propio hacia tu app
todavía — ver "Limitaciones conocidas" abajo).

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `PAYMENTS_ENABLED` | Activa/desactiva el módulo completo | `false` |
| `PAYMENT_PROVIDER` | Único valor soportado en v1 | `wompi` |
| `PAYMENTS_MIN_AMOUNT_CENTS` | Monto mínimo permitido, en centavos | `100000` (=$1.000 COP) |
| `PAYMENTS_MAX_AMOUNT_CENTS` | Monto máximo permitido, en centavos | `500000000` (=$5.000.000 COP) |
| `PAYMENTS_SUPPORTED_CURRENCIES` | Monedas aceptadas, separadas por coma | `COP` |
| `WOMPI_ENV` | `sandbox` o `production` | `sandbox` |
| `WOMPI_PUBLIC_KEY` | Llave pública (segura de exponer al frontend) | `pub_test_...` |
| `WOMPI_PRIVATE_KEY` | Llave privada — **solo backend**, usada para reembolsos | `prv_test_...` |
| `WOMPI_EVENTS_SECRET` | Secreto para verificar la firma del webhook — **solo backend** | — |
| `WOMPI_INTEGRITY_SECRET` | Secreto para la firma de integridad del checkout — **solo backend** | — |

## Endpoints

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/api/payments` | Usuario autenticado + rate limit | Crea una orden en `pendiente`, devuelve datos de checkout |
| `GET` | `/api/payments/{reference}` | Dueño de la orden o admin | Consulta el estado (única fuente de verdad para el frontend) |
| `GET` | `/api/payments` | Admin | Listado paginado (`?page=&limit=&status=`) |
| `POST` | `/api/payments/{reference}/refund` | Admin | Inicia reembolso contra Wompi |
| `POST` | `/api/payments/webhook/wompi` | Firma de Wompi (sin sesión) | Recibe confirmaciones asíncronas |

Formato de respuesta: este módulo usa `{success, data, error: {code, message}}`
(distinto del string plano del resto del proyecto — ver `docs/DECISIONS.md`).
Códigos realmente usados en el código (`payments/errors.py`/`payments/services/payment_service.py`):
`PAY_001_MONTO_INVALIDO`, `PAY_003_FIRMA_INVALIDA`,
`PAY_005_ORDEN_NO_ENCONTRADA`, `PAY_006_ESTADO_INVALIDO_PARA_REEMBOLSO`.
(Un monto de webhook que no coincide con la orden registrada NUNCA genera
un error HTTP -- se responde `200` igual a la pasarela por diseño, y la
discrepancia queda solo en los logs como `ANOMALIA`; no hay código de error
`PAY_004` porque nunca se expone como respuesta a un cliente.)

## Máquina de estados

```
pendiente ──webhook APROBADO + monto OK──▶ pagado ──refund (admin)──▶ reembolsado
    │
    └──webhook DECLINADO/ERROR/ANULADO──▶ fallido
```

`fallido` y `reembolsado` son terminales. Ningún endpoint permite fijar
`status` directamente por body de un cliente — el único camino a `pagado`
es un webhook con firma válida y monto coincidente; a `reembolsado`, una
acción explícita de admin.

## Seguridad (resumen — detalle completo en `docs/DECISIONS.md`)

- **Firma del webhook** verificada con SHA256 + comparación en tiempo
  constante (`hmac.compare_digest`) — nunca se procesa un webhook sin
  firma válida.
- **Monto siempre validado en backend**: un webhook nunca transiciona una
  orden a `pagado` si su monto no coincide exactamente con el registrado
  al crear la orden.
- **Idempotencia de doble capa**: índice único en eventos + update atómico
  condicionado al estado actual — un webhook duplicado nunca cobra dos
  veces ni dispara dos veces ningún efecto.
- **Secretos solo en `.env`** — nunca hardcodeados, nunca en `render.yaml`/
  `vercel.json` con valor fijo (usar `sync: false` en Render, variable de
  entorno del dashboard en Vercel si el frontend llegara a necesitar algo,
  hoy solo `WOMPI_PUBLIC_KEY` sería candidato y ni eso es necesario si el
  checkout se arma 100% en el backend, como está diseñado).

## Limitaciones conocidas

- **Sin SDK oficial de Wompi en Python** — el adaptador (`backend/payments/
  providers/wompi.py`) es un cliente HTTP propio sobre `httpx`. Mantenimiento
  manual si Wompi cambia su API.
- **Reembolsos**: la disponibilidad exacta vía API (total/parcial, ventana
  de tiempo) no está confirmada contra una cuenta real — puede que algunos
  casos solo se puedan hacer desde el back-office de Wompi. Si
  `POST /payments/{reference}/refund` falla contra tu cuenta real, revisá
  el panel de Wompi directamente.
- **Sin mecanismo propio de notificación hacia tu app anfitriona**: hoy,
  para enterarte de que un pago se confirmó tenés que hacer polling a
  `GET /payments/{reference}` o consultar la colección `payments`
  directamente. Un sistema de hooks (`on_payment_confirmed`) quedó
  propuesto en el diseño pero no implementado en v1.
- **Sin job de reconciliación**: si un webhook legítimo se pierde o falla
  la verificación de firma por un bug, la orden queda `pendiente`
  indefinidamente. No hay (todavía) un proceso que consulte proactivamente
  a Wompi el estado de órdenes `pendiente` viejas.
- **Cifras de comisión de Wompi** citadas en `docs/DECISIONS.md` tienen
  fecha de caducidad — reverificar en el dashboard antes de cualquier
  decisión comercial.
- **KYC para cobrar en producción** es un trámite de Wompi (NIT/Cámara de
  Comercio o cédula), no algo que este código resuelva — puede tardar de
  días a un par de semanas.
