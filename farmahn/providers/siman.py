from __future__ import annotations

from urllib.parse import quote, urljoin

import httpx

from farmahn.providers.base import PharmacyProvider, ProviderError
from farmahn.providers.browser import BrowserUnavailable, rendered_html
from farmahn.providers.generic_html import GenericProductParser


class SimanProvider(PharmacyProvider):
    name = "Farmacia Simán"
    slug = "siman"
    base_url = "https://www.farmaciasiman.com/"
    experimental = True

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def search(self, query: str, city: str | None = None):
        # Simán publica búsquedas bajo /busqueda/<termino>, pero el HTML crudo
        # contiene plantillas Angular; necesitamos ejecutar el JavaScript.
        search_url = urljoin(self.base_url, f"busqueda/{quote(query, safe='')}")

        try:
            html, final_url = await rendered_html(search_url)
        except BrowserUnavailable as exc:
            raise ProviderError(str(exc)) from exc
        except Exception as exc:
            raise ProviderError(
                f"No se pudo completar la búsqueda dinámica de {self.name}: {exc}"
            ) from exc

        items = GenericProductParser.parse(
            html,
            final_url,
            self.name,
            query=query,
            allow_missing_price=True,
        )
        if items:
            return items

        raise ProviderError(
            "Simán cargó la búsqueda, pero FarmaHN no pudo identificar "
            "productos después de ejecutar JavaScript."
        )
