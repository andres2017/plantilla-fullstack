import math
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


def estimate_cost(prompt: str) -> dict:
    """Heurística de costo (nunca se confía en el cliente)."""
    prompt_tokens = max(1, len(prompt) // 4)
    input_tokens = BUILDS_BASE_CONTEXT_TOKENS + prompt_tokens

    # Bucket de salida por tamaño de prompt
    if len(prompt) < 200:
        output_tokens = 3000
    elif len(prompt) < 800:
        output_tokens = 8000
    else:
        output_tokens = 15000

    cost = (
        (input_tokens / 1_000_000) * BUILDS_PRICE_INPUT_PER_MTOK_USD
        + (output_tokens / 1_000_000) * BUILDS_PRICE_OUTPUT_PER_MTOK_USD
    ) * BUILDS_ESTIMATE_SAFETY_MARGIN

    cost = min(cost, BUILDS_PER_BUILD_CAP_USD)  # nunca por encima del tope por build
    return {
        "estimated_cost_usd": round(cost, 4),
        "input_tokens_est": input_tokens,
        "output_tokens_est": output_tokens,
        "safety_margin": BUILDS_ESTIMATE_SAFETY_MARGIN,
    }


async def create_build(prompt: str, created_by: str) -> dict:
    # 1. Estimar server-side
    est = estimate_cost(prompt)
    estimated = est["estimated_cost_usd"]

    if estimated > BUILDS_PER_BUILD_CAP_USD:
        raise BuildHTTPException(
            400, "BUILD_002_COSTO_EXCEDIDO",
            f"El estimado (${estimated:.2f}) supera el tope por build (${BUILDS_PER_BUILD_CAP_USD:.2f})",
        )

    # 2. Chequeo de presupuesto diario (comprometido)
    spent, committed = await repo.get_today_spent_and_committed()
    if spent + committed + estimated > BUILDS_DAILY_BUDGET_USD:
        raise BuildHTTPException(
            400, "BUILD_003_PRESUPUESTO_DIARIO",
            f"No cabe en el presupuesto del día (disponible: ${max(0, BUILDS_DAILY_BUDGET_USD - spent - committed):.2f})",
        )

    # 3. Cola
    queued = await repo.count_queued()
    if queued >= BUILDS_MAX_QUEUE_DEPTH:
        raise BuildHTTPException(
            429, "BUILD_010_COLA_LLENA",
            f"Cola llena ({BUILDS_MAX_QUEUE_DEPTH} builds pendientes). Espera a que termine alguno.",
        )

    # 4. Crear
    build = await repo.create_build(prompt, estimated, created_by)
    return build


async def list_builds(page: int, limit: int, status: str | None = None):
    return await repo.list_builds(page, limit, status)


async def get_build(build_id: str) -> dict:
    build = await repo.get_build(build_id)
    if not build:
        raise BuildHTTPException(404, "BUILD_001_NO_ENCONTRADO", "Build no encontrado")
    return build
