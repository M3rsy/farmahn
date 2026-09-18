from __future__ import annotations

import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag

from farmahn.core.models import Product
from farmahn.core.normalize import extract_concentration, extract_quantity, normalize_text, parse_money


class GenericProductParser:
    """Parser tolerante para catálogos públicos que renderizan productos en HTML."""

    CARD_SELECTORS = (
        "li.product", ".product-card", ".product-item", ".product",
        ".card-product", ".item-product", "[class*='product-card']",
        "[class*='product-item']"
    )

    NAME_SELECTORS = (
        ".product-name", ".product-title", ".name", ".title",
        "h2", "h3", "h4"
    )

    @classmethod
    def parse(cls, html: str, page_url: str, pharmacy: str) -> list[Product]:
        # Angular/Vue templates sin hidratar no contienen resultados reales.
        if html.count("{$") > 5 and not re.search(r"L\.?\s*\d", html, re.I):
            return []

        soup = BeautifulSoup(html, "html.parser")
        cards: list[Tag] = []
        for selector in cls.CARD_SELECTORS:
            found = [node for node in soup.select(selector) if isinstance(node, Tag)]
            if found:
                cards = found
                break

        products: list[Product] = []
        seen: set[tuple[str, float, str]] = set()
        for card in cards:
            text = card.get_text(" ", strip=True)
            if not text:
                continue

            name_el = None
            for selector in cls.NAME_SELECTORS:
                name_el = card.select_one(selector)
                if name_el:
                    break
            if not name_el:
                continue

            name = name_el.get_text(" ", strip=True)
            if len(name) < 3 or "{$" in name:
                continue

            money_tokens = re.findall(r"(?:LPS\.?|L\.?|HNL)\s*\d[\d,]*(?:\.\d{1,2})?", text, re.I)
            prices = [parse_money(token) for token in money_tokens]
            prices = [price for price in prices if price is not None]
            if not prices:
                continue

            price = prices[-1]
            regular = prices[-2] if len(prices) >= 2 and prices[-2] >= price else None
            link = card.find("a", href=True)
            href = link.get("href") if isinstance(link, Tag) else None
            url = urljoin(page_url, href) if href else page_url

            lowered = normalize_text(text)
            available = None
            if any(word in lowered for word in ("AGOTADO", "SIN EXISTENCIA", "SIN INVENTARIO")):
                available = False
            elif any(word in lowered for word in ("DISPONIBLE", "EN STOCK", "AGREGAR")):
                available = True

            qty = extract_quantity(name)
            key = (normalize_text(name), price, url)
            if key in seen:
                continue
            seen.add(key)

            products.append(Product(
                pharmacy=pharmacy,
                name=name,
                price=price,
                regular_price=regular,
                url=url,
                quantity=qty,
                concentration=extract_concentration(name),
                unit_price=round(price / qty, 2) if qty and qty > 1 else None,
                available=available,
            ))
        return products
