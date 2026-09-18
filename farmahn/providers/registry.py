from farmahn.core.normalize import normalize_text
from farmahn.providers.san_antonio import SanAntonioProvider
from farmahn.providers.siman import SimanProvider
from farmahn.providers.kielsa import KielsaProvider
from farmahn.providers.ahorro import AhorroProvider


def get_providers(pharmacy: str | None = None):
    providers = [
        SanAntonioProvider(),
        SimanProvider(),
        KielsaProvider(),
        AhorroProvider(),
    ]
    if not pharmacy:
        return providers

    needle = normalize_text(pharmacy)
    return [
        provider
        for provider in providers
        if needle in normalize_text(provider.name)
        or needle == normalize_text(provider.slug)
        or needle in normalize_text(provider.slug)
    ]
