from __future__ import annotations
from farmahn.providers.base import PharmacyProvider
from farmahn.core.models import Product


class _PlannedProvider(PharmacyProvider):
    reason = "Proveedor reservado para la siguiente iteración"

    async def search(self, query: str, city: str | None = None) -> list[Product]:
        return []


class SimanProvider(_PlannedProvider):
    name = "Farmacia Simán"
    slug = "siman"


class KielsaProvider(_PlannedProvider):
    name = "Farmacias Kielsa"
    slug = "kielsa"


class AhorroProvider(_PlannedProvider):
    name = "Farmacias del Ahorro"
    slug = "ahorro"
