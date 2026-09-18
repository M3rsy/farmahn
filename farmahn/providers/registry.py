from farmahn.providers.san_antonio import SanAntonioProvider
from farmahn.providers.siman import SimanProvider
from farmahn.providers.kielsa import KielsaProvider
from farmahn.providers.ahorro import AhorroProvider


def get_providers(active_only: bool = True):
    # Desde v0.2 todas las integraciones participan en la búsqueda.
    # Las fuentes experimentales aíslan sus fallos mediante SearchEngine.
    return [
        SanAntonioProvider(),
        SimanProvider(),
        KielsaProvider(),
        AhorroProvider(),
    ]
