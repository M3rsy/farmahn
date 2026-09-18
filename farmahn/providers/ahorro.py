from __future__ import annotations

import httpx

from farmahn.providers.base import PharmacyProvider, ProviderError
from farmahn.providers.browser import BrowserUnavailable, search_form
from farmahn.providers.generic_html import GenericProductParser


class AhorroProvider(PharmacyProvider):
    name = "Farmacias del Ahorro"
    slug = "ahorro"
    base_url = "https://www.farmaciasdelahorro.hn/"
    experimental = True

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def search(self, query: str, city: str | None = None):
        # La búsqueda de Del Ahorro se genera desde JavaScript. El HTML inicial
        # no contiene las tarjetas que el usuario ve en pantalla.
        try:
            html, final_url = await search_form(
                self.base_url,
                query,
                placeholders=(
                    "Busca tu Medicamento",
                    "Busca tu medicamento",
                    "Buscar medicamento",
                ),
            )
        except BrowserUnavailable as exc:
            raise ProviderError(str(exc)) from exc
        except Exception as exc:
            raise ProviderError(
                f"No se pudo completar la búsqueda dinámica de {self.name}: {exc}"
            ) from exc

        # La página de resultados puede mostrar nombre + enlace antes de mostrar
        # precio. Conservamos esos resultados y los ordenamos después del último
        # producto con precio conocido.
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
            "Farmacias del Ahorro cargó la búsqueda, pero FarmaHN no pudo "
            "identificar las tarjetas de productos."
        )
