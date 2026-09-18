from __future__ import annotations

from abc import ABC, abstractmethod
from farmahn.core.models import Product


class ProviderError(RuntimeError):
    pass


class PharmacyProvider(ABC):
    name: str
    slug: str

    @abstractmethod
    async def search(self, query: str, city: str | None = None) -> list[Product]:
        raise NotImplementedError
