from __future__ import annotations

from urllib.parse import quote, urljoin

import httpx

from farmahn.providers.base import PharmacyProvider, ProviderError
from farmahn.providers.browser import BrowserUnavailable, rendered_html
from farmahn.providers.generic_html import GenericProductParser


class KielsaProvider(PharmacyProvider):
    name = "Farmacias Kielsa"
    slug = "kielsa"
    base_url = "https://www.kielsa.com/"
    experimental = True

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def search(self, query: str, city: str | None = None):
        # Esta es la ruta que usa el buscador web real de Kielsa.
        search_url = urljoin(
            self.base_url,
            f"searchproduct/1/TODAS/{quote(query, safe='')}",
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) FarmaHN/0.3.1",
            "Accept-Language": "es-HN,es;q=0.9",
        }

        # Primero probamos HTTP simple; si la página no ha hidratado los productos,
        # usamos Chromium headless para ejecutar el JavaScript del sitio.
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
                follow_redirects=True,
            ) as client:
                response = await client.get(search_url)
                response.raise_for_status()
                items = GenericProductParser.parse(
                    response.text,
                    str(response.url),
                    self.name,
                    query=query,
                )
                if items:
                    return items
        except httpx.HTTPError:
            pass

        try:
            html, final_url = await rendered_html(search_url)
        except BrowserUnavailable as exc:
            raise ProviderError(str(exc)) from exc

        items = GenericProductParser.parse(
            html,
            final_url,
            self.name,
            query=query,
        )
        if items:
            return items

        raise ProviderError(
            "Kielsa abrió la página de resultados, pero FarmaHN no pudo "
            "identificar las tarjetas de productos renderizadas."
        )
