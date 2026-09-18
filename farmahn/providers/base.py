from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter
import httpx

from farmahn.core.models import Product


class ProviderError(RuntimeError):
    pass


class PharmacyProvider(ABC):
    name: str
    slug: str
    base_url: str = ""

    @abstractmethod
    async def search(self, query: str, city: str | None = None) -> list[Product]:
        raise NotImplementedError

    async def healthcheck(self, timeout: float = 8.0) -> dict:
        if not self.base_url:
            return {
                "provider": self.name,
                "slug": self.slug,
                "ok": False,
                "status_code": None,
                "latency_ms": None,
                "error": "Provider sin base_url",
            }

        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(
                    self.base_url,
                    headers={"User-Agent": "Mozilla/5.0 FarmaHN/0.3 healthcheck"},
                )
            latency = round((perf_counter() - started) * 1000, 1)
            ok = 200 <= response.status_code < 500
            return {
                "provider": self.name,
                "slug": self.slug,
                "ok": ok,
                "status_code": response.status_code,
                "latency_ms": latency,
                "error": None if ok else f"HTTP {response.status_code}",
            }
        except Exception as exc:
            return {
                "provider": self.name,
                "slug": self.slug,
                "ok": False,
                "status_code": None,
                "latency_ms": round((perf_counter() - started) * 1000, 1),
                "error": str(exc),
            }
