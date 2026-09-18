from __future__ import annotations

from urllib.parse import urljoin
import httpx

from farmahn.core.normalize import normalize_text
from farmahn.providers.base import PharmacyProvider, ProviderError
from farmahn.providers.generic_html import GenericProductParser


class AhorroProvider(PharmacyProvider):
    name = "Farmacias del Ahorro"
    slug = "ahorro"
    base_url = "https://www.farmaciasdelahorro.hn/"
    experimental = True

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def search(self, query: str, city: str | None = None):
        attempts = [
            ("hn/products", {"search": query}),
            ("hn/products", {"q": query}),
            ("hn/products", {"query": query}),
            ("hn/products", {"term": query}),
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) FarmaHN/0.2",
            "Accept-Language": "es-HN,es;q=0.9",
        }
        last_error = None
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers, follow_redirects=True) as client:
            for path, params in attempts:
                try:
                    response = await client.get(urljoin(self.base_url, path), params=params)
                    response.raise_for_status()
                    
                    items = GenericProductParser.parse(response.text, str(response.url), self.name)
                    tokens = [t for t in normalize_text(query).split() if len(t) > 1]
                    items = [p for p in items if not tokens or any(t in normalize_text(p.name) for t in tokens)]
                    if items:
                        return sorted(items, key=lambda p: p.price)
                except httpx.HTTPError as exc:
                    last_error = exc

        if last_error:
            raise ProviderError(f"No se pudo consultar {self.name}: {last_error}")
        raise ProviderError(
            f"{self.name} respondió, pero no entregó productos renderizados en HTML. "
            "Es posible que la búsqueda dependa de una API dinámica que aún debe confirmarse."
        )
