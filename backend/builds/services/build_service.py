from datetime import datetime, timezone

from builds.config import (
    BUILDS_DAILY_BUDGET_USD,
    BUILDS_PER_BUILD_CAP_USD,
    BUILDS_MAX_QUEUE_DEPTH,
    BUILDS_BASE_CONTEXT_TOKENS,
    BUILDS_PRICE_INPUT_PER_MTOK_USD,
    BUILDS_PRICE_OUTPUT_PER_MTOK_USD,
    BUILDS_ESTIMATE_SAFETY_MARGIN,
)
from builds.errors import BuildHTTPException
from builds.repositories import build_repository as repo

# Multiplicadores suaves por tipo / modo (heurística, no confiar en el cliente)
_TYPE_MULT = {
    "full_stack": 1.0,
    "web_landing": 0.7,
    "backend_api": 0.6,
    "mobile_apk": 0.85,
    "custom": 1.0,
}
_MODE_MULT = {
    "learn": 0.45,
    "implement": 1.0,
}
_MODEL_MULT = {
    "haiku": 0.35,
    "sonnet": 1.0,
    "opus": 1.6,
}


def estimate_cost(
    prompt: str,
    *,
    template_type: str | None = None,
    mode: str = "implement",
    model: str | None = None,
) -> dict:
    prompt_tokens = max(1, len(prompt) // 4)
    input_tokens = BUILDS_BASE_CONTEXT_TOKENS + prompt_tokens

    if len(prompt) < 200:
        output_tokens = 3000
    elif len(prompt) < 800:
        output_tokens = 8000
    else:
        output_tokens = 15000

    if mode == "learn":
        output_tokens = min(output_tokens, 4000)

    cost = (
        (input_tokens / 1_000_000) * BUILDS_PRICE_INPUT_PER_MTOK_USD
        + (output_tokens / 1_000_000) * BUILDS_PRICE_OUTPUT_PER_MTOK_USD
    ) * BUILDS_ESTIMATE_SAFETY_MARGIN

    cost *= _TYPE_MULT.get(template_type or "custom", 1.0)
    cost *= _MODE_MULT.get(mode or "implement", 1.0)
    cost *= _MODEL_MULT.get(model or "sonnet", 1.0)

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
    *,
    created_by_email: str | None = None,
    template_type: str | None = None,
    blueprint_step_id: str | None = None,
    blueprint_version: str | None = None,
    mode: str = "implement",
    agent: str | None = None,
    model: str | None = None,
    locale: str = "es",
) -> dict:
    est = estimate_cost(prompt, template_type=template_type, mode=mode, model=model)
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
        prompt,
        estimated,
        created_by,
        created_by_email=created_by_email,
        template_type=template_type,
        blueprint_step_id=blueprint_step_id,
        blueprint_version=blueprint_version,
        mode=mode or "implement",
        agent=agent,
        model=model,
        locale=locale or "es",
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
    log = []
    for ev in events or []:
        if isinstance(ev, dict) and "ts" in ev and "message" in ev:
            log.append(ev)
            continue
        text = str(ev)
        if text.startswith("[") and "]" in text:
            end = text.index("]")
            ts = text[1:end]
            message = text[end + 1:].strip()
            log.append({"ts": ts, "message": message})
        else:
            log.append({"ts": datetime.now(timezone.utc).isoformat(), "message": text})
    return log
