from datetime import datetime, timezone

from builds.config import (
    BUILDS_DAILY_BUDGET_USD,
    BUILDS_PER_BUILD_CAP_USD,
    BUILDS_MAX_QUEUE_DEPTH,
    BUILDS_BASE_CONTEXT_TOKENS,
    BUILDS_ESTIMATE_SAFETY_MARGIN,
    BUILDS_MODEL_PRICING,
)
from builds.errors import BuildHTTPException
from builds.repositories import build_repository as repo

# Multiplicador sobre BUILDS_BASE_CONTEXT_TOKENS segun cuanto contexto de la
# plantilla necesita leer el agente para ese tipo de entrega. Heuristica, no
# medicion exacta — ajustable aqui sin tocar el resto del flujo.
_TEMPLATE_CONTEXT_MULTIPLIER = {
    "full_stack": 1.0,    # backend + frontend completos
    "web_landing": 0.5,   # solo frontend, alcance chico
    "mobile_apk": 0.8,    # capa Capacitor/Android, contexto moderado
    "backend_only": 0.6,  # solo backend
    "custom": 1.0,        # sin restriccion de alcance, asumir el caso base
}


def estimate_cost(prompt: str, template_type: str = "full_stack", model: str = "sonnet") -> dict:
    """Heuristica de costo (nunca se confia en el cliente)."""
    multiplier = _TEMPLATE_CONTEXT_MULTIPLIER.get(template_type, 1.0)
    prompt_tokens = max(1, len(prompt) // 4)
    input_tokens = int(BUILDS_BASE_CONTEXT_TOKENS * multiplier) + prompt_tokens

    if len(prompt) < 200:
        output_tokens = 3000
    elif len(prompt) < 800:
        output_tokens = 8000
    else:
        output_tokens = 15000

    pricing = BUILDS_MODEL_PRICING.get(model, BUILDS_MODEL_PRICING["sonnet"])
    cost = (
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"]
    ) * BUILDS_ESTIMATE_SAFETY_MARGIN

    cost = min(cost, BUILDS_PER_BUILD_CAP_USD)
    return {
        "estimated_cost_usd": round(cost, 4),
        "input_tokens_est": input_tokens,
        "output_tokens_est": output_tokens,
        "safety_margin": BUILDS_ESTIMATE_SAFETY_MARGIN,
    }


async def create_build(
    prompt: str,
    created_by: str,
    created_by_email: str = "",
    template_type: str = "full_stack",
    agent: str = "implementer",
    model: str = "sonnet",
) -> dict:
    est = estimate_cost(prompt, template_type, model)
    estimated = est["estimated_cost_usd"]

    if estimated > BUILDS_PER_BUILD_CAP_USD:
        raise BuildHTTPException(
            400, "BUILD_002_COSTO_EXCEDIDO",
            f"El estimado (${estimated:.2f}) supera el tope por build (${BUILDS_PER_BUILD_CAP_USD:.2f})",
        )

    spent, committed = await repo.get_today_spent_and_committed()
    if spent + committed + estimated > BUILDS_DAILY_BUDGET_USD:
        raise BuildHTTPException(
            400, "BUILD_003_PRESUPUESTO_DIARIO",
            f"No cabe en el presupuesto del dia (disponible: ${max(0, BUILDS_DAILY_BUDGET_USD - spent - committed):.2f})",
        )

    queued = await repo.count_queued()
    if queued >= BUILDS_MAX_QUEUE_DEPTH:
        raise BuildHTTPException(
            429, "BUILD_010_COLA_LLENA",
            f"Cola llena ({BUILDS_MAX_QUEUE_DEPTH} builds pendientes). Espera a que termine alguno.",
        )

    build = await repo.create_build(
        prompt, estimated, created_by,
        created_by_email=created_by_email,
        template_type=template_type,
        agent=agent,
        model=model,
    )
    return build


async def list_builds(page: int, limit: int, status: str | None = None):
    return await repo.list_builds(page, limit, status)


async def get_build(build_id: str) -> dict:
    build = await repo.get_build(build_id)
    if not build:
        raise BuildHTTPException(404, "BUILD_001_NO_ENCONTRADO", "Build no encontrado")
    return build


async def cancel_build(build_id: str) -> dict:
    build = await repo.get_build(build_id)
    if not build:
        raise BuildHTTPException(404, "BUILD_001_NO_ENCONTRADO", "Build no encontrado")

    if build["status"] not in ("queued", "running"):
        raise BuildHTTPException(
            400, "BUILD_004_NO_CANCELABLE",
            f"No se puede cancelar un build en estado '{build['status']}'",
        )

    now = datetime.now(timezone.utc)
    updated = await repo.update_build(
        build_id,
        status="cancelled",
        finished_at=now,
        actual_cost_usd=0.0,
        error_code="BUILD_005_CANCELADO",
        error_message="Cancelado por el administrador",
    )
    await repo.append_event(build_id, f"[{now.isoformat()}] Cancelado por el administrador")

    # Avisar a suscriptores SSE si el worker aun no lo noto
    try:
        from builds.services import worker
        await worker.publish(build_id, "status", {"status": "cancelled", "queue_position": None})
        await worker.publish(build_id, "done", {
            "status": "cancelled",
            "cost_real_usd": 0.0,
            "download_url": None,
        })
    except Exception:
        pass

    return updated


def parse_progress_log(events: list) -> list:
    """Convierte eventos string del repo a [{ts, message}] para el frontend."""
    log = []
    for ev in events or []:
        if isinstance(ev, dict) and "ts" in ev and "message" in ev:
            log.append(ev)
            continue
        text = str(ev)
        # Formato "[iso] mensaje"
        if text.startswith("[") and "]" in text:
            end = text.index("]")
            ts = text[1:end]
            message = text[end + 1:].strip()
            log.append({"ts": ts, "message": message})
        else:
            log.append({"ts": datetime.now(timezone.utc).isoformat(), "message": text})
    return log
