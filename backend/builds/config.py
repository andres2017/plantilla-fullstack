# Config del modulo de builds. TODO se lee con .get() (nunca os.environ[...]
# obligatorio a nivel de import), para que un proyecto sin BUILDS_ENABLED
# arranque exactamente igual que sin este modulo.
import logging
import os

logger = logging.getLogger("builds.config")

BUILDS_ENABLED = os.environ.get("BUILDS_ENABLED", "false").strip().lower() == "true"

# Tope diario global (USD) y tope por build individual.
# Defaults generosos: $0.50 cortaba builds reales de ideación/implementación.
BUILDS_DAILY_BUDGET_USD = float(os.environ.get("BUILDS_DAILY_BUDGET_USD", "50"))
BUILDS_PER_BUILD_CAP_USD = float(os.environ.get("BUILDS_PER_BUILD_CAP_USD", "5.00"))

# Cola y concurrencia
BUILDS_MAX_QUEUE_DEPTH = int(os.environ.get("BUILDS_MAX_QUEUE_DEPTH", "10"))
BUILDS_MAX_TURNS = int(os.environ.get("BUILDS_MAX_TURNS", "60"))
BUILDS_TIMEOUT_SECONDS = int(os.environ.get("BUILDS_TIMEOUT_SECONDS", "900"))

# Estimacion de costo base (Sonnet) — USD por millon de tokens
BUILDS_PRICE_INPUT_PER_MTOK_USD = float(os.environ.get("BUILDS_PRICE_INPUT_PER_MTOK_USD", "3.00"))
BUILDS_PRICE_OUTPUT_PER_MTOK_USD = float(os.environ.get("BUILDS_PRICE_OUTPUT_PER_MTOK_USD", "15.00"))
BUILDS_ESTIMATE_SAFETY_MARGIN = float(os.environ.get("BUILDS_ESTIMATE_SAFETY_MARGIN", "1.15"))
BUILDS_BASE_CONTEXT_TOKENS = int(os.environ.get("BUILDS_BASE_CONTEXT_TOKENS", "8000"))

# Catalogo de modelos (alias UI -> model id Anthropic)
BUILDS_MODEL_HAIKU = os.environ.get("BUILDS_MODEL_HAIKU", "claude-haiku-4-5-20251001")
BUILDS_MODEL_SONNET = os.environ.get("BUILDS_MODEL_SONNET", "claude-sonnet-5")
BUILDS_MODEL_OPUS = os.environ.get("BUILDS_MODEL_OPUS", "claude-opus-4-8")
BUILDS_MODEL_MAP = {
    "haiku": BUILDS_MODEL_HAIKU,
    "sonnet": BUILDS_MODEL_SONNET,
    "opus": BUILDS_MODEL_OPUS,
}

BUILDS_PRICE_HAIKU_INPUT = float(os.environ.get("BUILDS_PRICE_HAIKU_INPUT", "1.00"))
BUILDS_PRICE_HAIKU_OUTPUT = float(os.environ.get("BUILDS_PRICE_HAIKU_OUTPUT", "5.00"))
BUILDS_PRICE_OPUS_INPUT = float(os.environ.get("BUILDS_PRICE_OPUS_INPUT", "15.00"))
BUILDS_PRICE_OPUS_OUTPUT = float(os.environ.get("BUILDS_PRICE_OPUS_OUTPUT", "75.00"))
BUILDS_MODEL_PRICING = {
    "haiku": {"input": BUILDS_PRICE_HAIKU_INPUT, "output": BUILDS_PRICE_HAIKU_OUTPUT},
    "sonnet": {"input": BUILDS_PRICE_INPUT_PER_MTOK_USD, "output": BUILDS_PRICE_OUTPUT_PER_MTOK_USD},
    "opus": {"input": BUILDS_PRICE_OPUS_INPUT, "output": BUILDS_PRICE_OPUS_OUTPUT},
}

# Presupuesto Agent SDK por modo (fraccion del tope por build)
BUILDS_LEARN_BUDGET_USD = float(
    os.environ.get("BUILDS_LEARN_BUDGET_USD", str(min(2.0, BUILDS_PER_BUILD_CAP_USD)))
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
BUILDS_WORK_ROOT = os.environ.get("BUILDS_WORK_ROOT", "/tmp/builds")
BUILDS_TEMPLATE_ROOT = os.environ.get("BUILDS_TEMPLATE_ROOT", "").strip() or None


def agent_mode_enabled() -> bool:
    return bool(ANTHROPIC_API_KEY)


def budget_for_mode(mode: str) -> float:
    """USD max que el Agent SDK puede gastar en una corrida."""
    if mode == "learn":
        return max(0.25, min(BUILDS_LEARN_BUDGET_USD, BUILDS_PER_BUILD_CAP_USD))
    return max(0.5, BUILDS_PER_BUILD_CAP_USD)


def validate_builds_config():
    if agent_mode_enabled():
        logger.info("Builds: modo AGENT SDK real (ANTHROPIC_API_KEY presente)")
    else:
        logger.warning(
            "BUILDS_ENABLED=true sin ANTHROPIC_API_KEY — worker en modo STUB. "
            "Agrega la clave para activar Claude Agent SDK."
        )
    logger.info(
        "Builds budget: per_build=$%.2f daily=$%.2f learn_cap=$%.2f",
        BUILDS_PER_BUILD_CAP_USD,
        BUILDS_DAILY_BUDGET_USD,
        BUILDS_LEARN_BUDGET_USD,
    )
