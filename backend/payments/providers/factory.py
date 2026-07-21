from payments.config import PAYMENT_PROVIDER
from payments.providers.base import PaymentProvider
from payments.providers.wompi import WompiProvider

_provider_instance: PaymentProvider | None = None


def get_provider() -> PaymentProvider:
    global _provider_instance
    if _provider_instance is None:
        if PAYMENT_PROVIDER == "wompi":
            _provider_instance = WompiProvider()
        else:
            raise RuntimeError(f"PAYMENT_PROVIDER='{PAYMENT_PROVIDER}' no soportado (solo 'wompi' en v1).")
    return _provider_instance
