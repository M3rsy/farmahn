from __future__ import annotations

from urllib.parse import urljoin
import re
import httpx
from bs4 import BeautifulSoup, Tag

from farmahn.core.models import Product
from farmahn.core.normalize import parse_money, extract_quantity, extract_concentration, normalize_text
from farmahn.providers.base import PharmacyProvider, ProviderError


class SanAntonioProvider(PharmacyProvider):
    name = "Farmacia San Antonio"
    slug = "san-antonio"
    base_url = "https://www.farmaciasanantonio.hn/"

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def search(self, query: str, city: str | None = None) -> list[Product]:
        attempts = [
            ("GET", "Buscar/", {"buscar": query}),
            ("GET", "Buscar/", {"search": query}),
            ("GET", "Buscar/", {"s": query}),
            ("GET", "", {"s": query, "post_type": "product"}),
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) FarmaHN/0.3",
            "Accept-Language": "es-HN,es;q=0.9",
        }
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers, follow_redirects=True) as client:
            for method, path, params in attempts:
                try:
                    response = await client.request(method, urljoin(self.base_url, path), params=params)
                    response.raise_for_status()
                    products = self.parse_search_html(response.text, response.url)
                    products = self._filter_query(products, query)
                    if products:
                        return products
                except (httpx.HTTPError, ValueError) as exc:
                    last_error = exc
                    continue
        if last_error:
            raise ProviderError(f"No se pudo consultar {self.name}: {last_error}")
        return []

    @staticmethod
    def _filter_query(products: list[Product], query: str) -> list[Product]:
        tokens = [t for t in normalize_text(query).split() if len(t) > 1]
        if not tokens:
            return products
        scored = []
        for p in products:
            n = normalize_text(p.name)
            score = sum(token in n for token in tokens)
            if score:
                scored.append((score, p))
        scored.sort(key=lambda x: (-x[0], x[1].price))
        return [p for _, p in scored]

    @classmethod
    def parse_search_html(cls, html: str, page_url: str | httpx.URL) -> list[Product]:
        soup = BeautifulSoup(html, "html.parser")
        base = str(page_url)
        products: list[Product] = []
        seen: set[tuple[str, float]] = set()

        selectors = [
            "li.product", ".product", ".products .item", ".product-item",
            ".woocommerce-loop-product", ".col-product", "article"
        ]
        cards: list[Tag] = []
        for selector in selectors:
            found = [x for x in soup.select(selector) if isinstance(x, Tag)]
            if found:
                cards = found
                break

        if not cards:
            for h in soup.find_all(["h2", "h3", "h4"]):
                if h.get_text(" ", strip=True):
                    parent = h.find_parent(["li", "article", "div"])
                    if isinstance(parent, Tag):
                        cards.append(parent)

        for card in cards:
            text = card.get_text(" ", strip=True)
            if not text or "L" not in text.upper():
                continue

            name_el = card.select_one("h2, h3, h4, .woocommerce-loop-product__title, .product-title, .title")
            if not name_el:
                continue
            name = name_el.get_text(" ", strip=True)
            if len(name) < 3:
                continue

            raw_prices = re.findall(r"(?:L\.?\s*)?\d[\d,]*(?:\.\d{1,2})", text, flags=re.I)
            prices = [parse_money(x) for x in raw_prices]
            prices = [p for p in prices if p is not None]

            currency_prices = re.findall(r"L\.?\s*\d[\d,]*(?:\.\d{1,2})", text, flags=re.I)
            cp = [parse_money(x) for x in currency_prices]
            cp = [p for p in cp if p is not None]
            if cp:
                prices = cp
            if not prices:
                continue

            price = prices[-1]
            regular = prices[-2] if len(prices) >= 2 and prices[-2] >= price else None

            anchor = name_el.find_parent("a") or card.find("a", href=True)
            href = anchor.get("href") if isinstance(anchor, Tag) else None
            url = urljoin(base, href) if href else base

            qty = extract_quantity(name)
            key = (normalize_text(name), price)
            if key in seen:
                continue
            seen.add(key)
            products.append(Product(
                pharmacy=cls.name,
                name=name,
                price=price,
                regular_price=regular,
                url=url,
                quantity=qty,
                concentration=extract_concentration(name),
                unit_price=round(price / qty, 2) if qty and qty > 1 else None,
            ))
        return products
