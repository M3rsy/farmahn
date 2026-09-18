from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from farmahn.core.models import Product
from farmahn.core.normalize import (
    extract_concentration,
    extract_quantity,
    normalize_text,
    parse_money,
    relevance_score,
)
from farmahn.providers.base import PharmacyProvider, ProviderError
from farmahn.providers.browser import BrowserUnavailable, search_form
from farmahn.providers.generic_html import GenericProductParser


class SanAntonioProvider(PharmacyProvider):
    name = "Farmacia San Antonio"
    slug = "san-antonio"
    base_url = "https://www.farmaciasanantonio.hn/"
    experimental = False
    supports_offers = True
    supports_stock = False

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def search(self, query: str, city: str | None = None) -> list[Product]:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) FarmaHN/0.3.1",
            "Accept-Language": "es-HN,es;q=0.9",
        }

        # Intentamos primero las variantes HTTP conocidas por compatibilidad.
        attempts = [
            ("Buscar/", {"buscar": query}),
            ("Buscar/", {"search": query}),
            ("Buscar/", {"s": query}),
            ("Tienda/", {"search": query}),
            ("Tienda/", {"q": query}),
        ]
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=headers,
            follow_redirects=True,
        ) as client:
            for path, params in attempts:
                try:
                    response = await client.get(urljoin(self.base_url, path), params=params)
                    response.raise_for_status()
                    products = self.parse_search_html(response.text, response.url)
                    products = self._filter_query(products, query)
                    if products:
                        return products
                except httpx.HTTPError:
                    continue

        # El formulario del sitio conoce el parámetro/acción actual. Si la
        # búsqueda HTTP no funciona, reproducimos la búsqueda del navegador.
        try:
            html, final_url = await search_form(
                urljoin(self.base_url, "Buscar/"),
                query,
                placeholders=("Buscar productos", "Buscar productos…"),
            )
        except BrowserUnavailable as exc:
            raise ProviderError(str(exc)) from exc
        except Exception as exc:
            raise ProviderError(
                f"No se pudo completar la búsqueda de {self.name}: {exc}"
            ) from exc

        products = self.parse_search_html(html, final_url)
        if not products:
            products = GenericProductParser.parse(
                html,
                final_url,
                self.name,
                query=query,
            )

        products = self._filter_query(products, query)
        if products:
            return products

        raise ProviderError(
            "Farmacia San Antonio cargó la búsqueda, pero no se pudieron "
            "identificar productos en el resultado."
        )

    @staticmethod
    def _filter_query(products: list[Product], query: str) -> list[Product]:
        # Fuzzy matching: evita perder resultados por pequeñas variaciones/errores.
        filtered = [
            product
            for product in products
            if relevance_score(query, product.name) >= 45
        ]
        filtered.sort(
            key=lambda product: (
                -relevance_score(query, product.name),
                product.price if product.price is not None else float("inf"),
            )
        )
        return filtered

    @classmethod
    def parse_search_html(
        cls,
        html: str,
        page_url: str | httpx.URL,
    ) -> list[Product]:
        soup = BeautifulSoup(html, "html.parser")
        base = str(page_url)
        products: list[Product] = []
        seen: set[tuple[str, float, str]] = set()

        selectors = [
            "li.product",
            ".product",
            ".products .item",
            ".product-item",
            ".woocommerce-loop-product",
            ".col-product",
            "article",
        ]
        cards: list[Tag] = []
        for selector in selectors:
            found = [node for node in soup.select(selector) if isinstance(node, Tag)]
            if found:
                cards = found
                break

        if not cards:
            for heading in soup.find_all(["h2", "h3", "h4"]):
                if heading.get_text(" ", strip=True):
                    parent = heading.find_parent(["li", "article", "div"])
                    if isinstance(parent, Tag):
                        cards.append(parent)

        for card in cards:
            text = card.get_text(" ", strip=True)
            if not text or "L" not in text.upper():
                continue

            name_el = card.select_one(
                "h2, h3, h4, .woocommerce-loop-product__title, "
                ".product-title, .title"
            )
            if not name_el:
                continue

            name = name_el.get_text(" ", strip=True)
            if len(name) < 3:
                continue

            currency_prices = re.findall(
                r"L\.?\s*\d[\d,]*(?:\.\d{1,2})",
                text,
                flags=re.I,
            )
            prices = [parse_money(value) for value in currency_prices]
            prices = [value for value in prices if value is not None]
            if not prices:
                continue

            price = prices[-1]
            regular = prices[-2] if len(prices) >= 2 and prices[-2] >= price else None

            anchor = name_el.find_parent("a") or card.find("a", href=True)
            href = anchor.get("href") if isinstance(anchor, Tag) else None
            url = urljoin(base, href) if href else base

            qty = extract_quantity(name)
            normalized_card = normalize_text(text)
            available = None
            if any(flag in normalized_card for flag in ("AGOTADO", "SIN EXISTENCIA")):
                available = False
            elif "EN STOCK" in normalized_card or "AGREGAR AL CARRITO" in normalized_card:
                available = True

            key = (normalize_text(name), price, url)
            if key in seen:
                continue
            seen.add(key)

            products.append(
                Product(
                    pharmacy=cls.name,
                    name=name,
                    price=price,
                    regular_price=regular,
                    url=url,
                    quantity=qty,
                    concentration=extract_concentration(name),
                    unit_price=round(price / qty, 2) if qty and qty > 1 else None,
                    available=available,
                )
            )

        return products
