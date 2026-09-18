from __future__ import annotations

import asyncio
from dataclasses import dataclass
from farmahn.providers.base import PharmacyProvider


@dataclass
class ProviderStatus:
    provider: str
    ok: bool
    count: int = 0
    error: str | None = None


async def search_all(providers: list[PharmacyProvider], query: str, city: str | None = None):
    async def run(provider: PharmacyProvider):
        try:
            items = await provider.search(query, city=city)
            return items, ProviderStatus(provider.name, True, len(items))
        except Exception as exc:
            return [], ProviderStatus(provider.name, False, 0, str(exc))

    batches = await asyncio.gather(*(run(p) for p in providers))
    products = [item for items, _ in batches for item in items]
    products.sort(key=lambda p: p.price)
    statuses = [status for _, status in batches]
    return products, statuses
