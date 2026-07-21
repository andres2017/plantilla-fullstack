# Config del modulo de pagos: a diferencia de core/config.py, TODO se lee con
# .get() (nunca os.environ[...] obligatorio a nivel de import), para que un
# proyecto sin credenciales de Wompi configuradas arranque exactamente igual
# que sin este modulo cuando PAYMENTS_ENABLED esta apagado/ausente.
import os

PAYMENTS_ENABLED = os.environ.get("PAYMENTS_ENABLED", "false").strip().lower() == "true"
PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "wompi").strip().lower()

PAYMENTS_MIN_AMOUNT_CENTS = int(os.environ.get("PAYMENTS_MIN_AMOUNT_CENTS", "100000"))
PAYMENTS_MAX_AMOUNT_CENTS = int(os.environ.get("PAYMENTS_MAX_AMOUNT_CENTS", "500000000"))
PAYMENTS_SUPPORTED_CURRENCIES = [
    c.strip().upper()
    for c in os.environ.get("PAYMENTS_SUPPORTED_CURRENCIES", "COP").split(",")
    if c.strip()
]

WOMPI_ENV = os.environ.get("WOMPI_ENV", "sandbox").strip().lower()
WOMPI_PUBLIC_KEY = os.environ.get("WOMPI_PUBLIC_KEY")
WOMPI_PRIVATE_KEY = os.environ.get("WOMPI_PRIVATE_KEY")
WOMPI_EVENTS_SECRET = os.environ.get("WOMPI_EVENTS_SECRET")
WOMPI_INTEGRITY_SECRET = os.environ.get("WOMPI_INTEGRITY_SECRET")


def validate_payments_config():
    """Fail-fast, pero SOLO se invoca cuando PAYMENTS_ENABLED=true (ver
    server.py) -- nunca a nivel de import de este modulo, para no romper el
    arranque de proyectos que no usan pagos."""
    if PAYMENT_PROVIDER == "wompi":
        faltantes = [
            name for name, value in [
                ("WOMPI_PUBLIC_KEY", WOMPI_PUBLIC_KEY),
                ("WOMPI_PRIVATE_KEY", WOMPI_PRIVATE_KEY),
                ("WOMPI_EVENTS_SECRET", WOMPI_EVENTS_SECRET),
                ("WOMPI_INTEGRITY_SECRET", WOMPI_INTEGRITY_SECRET),
            ] if not value
        ]
        if faltantes:
            raise RuntimeError(
                "PAYMENTS_ENABLED=true con PAYMENT_PROVIDER=wompi requiere: "
                f"{', '.join(faltantes)}. Revisa backend/.env."
            )
    else:
        raise RuntimeError(f"PAYMENT_PROVIDER='{PAYMENT_PROVIDER}' no soportado (solo 'wompi' en v1).")
