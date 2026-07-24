# Config del modulo de builds. TODO se lee con .get() (nunca os.environ[...]
# obligatorio a nivel de import), para que un proyecto sin BUILDS_ENABLED
# arranque exactamente igual que sin este modulo.
import logging
import os

logger = logging.getLogger("builds.config")

BUILDS_ENABLED = os.environ.get("BUILDS_ENABLED", "false").strip().lower() == "true"

# Tope diario global (USD) y tope por build individual
BUILDS_DAILY_BUDGET_USD = float(os.environ.get("BUILDS_DAILY_BUDGET_USD", "20"))
BUILDS_PER_BUILD_CAP_USD = float(os.environ.get("BUILDS_PER_BUILD_CAP_USD", "0.50"))

# Cola y concurrencia
BUILDS_MAX_QUEUE_DEPTH = int(os.environ.get("BUILDS_MAX_QUEUE_DEPTH", "10"))
BUILDS_MAX_TURNS = int(os.environ.get("BUILDS_MAX_TURNS", "40"))
BUILDS_TIMEOUT_SECONDS = int(os.environ.get("BUILDS_TIMEOUT_SECONDS", "600"))

# Estimacion de costo (tarifas Sonnet, actualizables sin tocar codigo)
BUILDS_PRICE_INPUT_PER_MTOK_USD = float(os.environ.get("BUILDS_PRICE_INPUT_PER_MTOK_USD", "3.00"))
BUILDS_PRICE_OUTPUT_PER_MTOK_USD = float(os.environ.get("BUILDS_PRICE_OUTPUT_PER_MTOK_USD", "15.00"))
BUILDS_ESTIMATE_SAFETY_MARGIN = float(os.environ.get("BUILDS_ESTIMATE_SAFETY_MARGIN", "1.3"))
BUILDS_BASE_CONTEXT_TOKENS = int(os.environ.get("BUILDS_BASE_CONTEXT_TOKENS", "12000"))

# Catalogo de modelos (alias amigable de la UI -> model id real de Anthropic).
# Los id por defecto son los vigentes al momento de escribir esto; si Anthropic
# libera modelos nuevos, se actualizan aqui via env sin tocar codigo.
BUILDS_MODEL_HAIKU = os.environ.get("BUILDS_MODEL_HAIKU", "claude-haiku-4-5-20251001")
BUILDS_MODEL_SONNET = os.environ.get("BUILDS_MODEL_SONNET", "claude-sonnet-5")
BUILDS_MODEL_OPUS = os.environ.get("BUILDS_MODEL_OPUS", "claude-opus-4-8")
BUILDS_MODEL_MAP = {
    "haiku": BUILDS_MODEL_HAIKU,
    "sonnet": BUILDS_MODEL_SONNET,
    "opus": BUILDS_MODEL_OPUS,
}

# Tarifas por tier (USD por millon de tokens) para que el estimate refleje el
# modelo elegido, no solo el tamano del prompt. Aproximadas y ajustables por
# env — el estimate ya lleva BUILDS_ESTIMATE_SAFETY_MARGIN como colchon.
BUILDS_PRICE_HAIKU_INPUT = float(os.environ.get("BUILDS_PRICE_HAIKU_INPUT", "1.00"))
BUILDS_PRICE_HAIKU_OUTPUT = float(os.environ.get("BUILDS_PRICE_HAIKU_OUTPUT", "5.00"))
BUILDS_PRICE_OPUS_INPUT = float(os.environ.get("BUILDS_PRICE_OPUS_INPUT", "15.00"))
BUILDS_PRICE_OPUS_OUTPUT = float(os.environ.get("BUILDS_PRICE_OPUS_OUTPUT", "75.00"))
BUILDS_MODEL_PRICING = {
    "haiku": {"input": BUILDS_PRICE_HAIKU_INPUT, "output": BUILDS_PRICE_HAIKU_OUTPUT},
    "sonnet": {"input": BUILDS_PRICE_INPUT_PER_MTOK_USD, "output": BUILDS_PRICE_OUTPUT_PER_MTOK_USD},
    "opus": {"input": BUILDS_PRICE_OPUS_INPUT, "output": BUILDS_PRICE_OPUS_OUTPUT},
}

# API key de Anthropic. Si esta presente → Agent SDK real; si no → worker stub.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Directorio base donde se crean los working dirs de cada build
BUILDS_WORK_ROOT = os.environ.get("BUILDS_WORK_ROOT", "/tmp/builds")

# Raiz de la plantilla a copiar. Vacio = se deduce (repo root relativo a este archivo).
BUILDS_TEMPLATE_ROOT = os.environ.get("BUILDS_TEMPLATE_ROOT", "").strip() or None


def agent_mode_enabled() -> bool:
    return bool(ANTHROPIC_API_KEY)


def validate_builds_config():
    """Validacion al activar el modulo."""
    if agent_mode_enabled():
        logger.info("Builds: modo AGENT SDK real (ANTHROPIC_API_KEY presente)")
    else:
        logger.warning(
            "BUILDS_ENABLED=true sin ANTHROPIC_API_KEY — worker en modo STUB. "
            "Agrega la clave para activar Claude Agent SDK."
        )
