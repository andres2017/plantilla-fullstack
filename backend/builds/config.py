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

# API key de Anthropic. En v1 (worker stub) es opcional.
# Cuando se active el Agent SDK real, se volvera obligatoria.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Directorio base donde se crean los working dirs de cada build
BUILDS_WORK_ROOT = os.environ.get("BUILDS_WORK_ROOT", "/tmp/builds")


def validate_builds_config():
    """Validacion al activar el modulo. En modo stub no exige API key."""
    if not ANTHROPIC_API_KEY:
        logger.warning(
            "BUILDS_ENABLED=true sin ANTHROPIC_API_KEY — worker en modo STUB. "
            "El Agent SDK real requerira la clave."
        )
