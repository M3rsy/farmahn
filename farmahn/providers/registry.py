from farmahn.providers.san_antonio import SanAntonioProvider
from farmahn.providers.stubs import SimanProvider, KielsaProvider, AhorroProvider


def get_providers(active_only: bool = True):
    providers = [SanAntonioProvider()]
    if not active_only:
        providers += [SimanProvider(), KielsaProvider(), AhorroProvider()]
    return providers
