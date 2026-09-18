from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from farmahn.core.models import Product
from farmahn.core.normalize import (
    extract_concentration,
    extract_quantity,
    normalize_text,
    parse_money,
    relevance_score,
)


class GenericProductParser:
    """Parser tolerante para catálogos públicos ya renderizados."""

    CARD_SELECTORS = (
        "li.product",
        ".product-card",
        ".product-item",
        ".product",
        ".card-product",
        ".item-product",
        "[class*='product-card']",
        "[class*='product-item']",
        ".card",
        "[class*='productCard']",
        "article",
    )

    NAME_SELECTORS = (
        ".product-name",
        ".product-title",
        ".name",
        ".title",
        "[class*='product-name']",
        "[class*='product-title']",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
    )

    @classmethod
    def _candidate_cards(cls, soup: BeautifulSoup) -> list[Tag]:
        cards: list[Tag] = []
        seen: set[int] = set()

        for selector in cls.CARD_SELECTORS:
            for node in soup.select(selector):
                if isinstance(node, Tag) and id(node) not in seen:
                    text = node.get_text(" ", strip=True)
                    if 8 <= len(text) <= 1800:
                        cards.append(node)
                        seen.add(id(node))

        # Fallback para sitios cuyos botones son "VER MÁS", "VER PRODUCTO" o "AGREGAR".
        for anchor in soup.find_all("a", href=True):
            label = normalize_text(anchor.get_text(" ", strip=True))
            if not any(key in label for key in ("VER MAS", "VER PRODUCTO", "AGREGAR", "AVISO CUANDO")):
                continue
            parent = anchor
            for _ in range(6):
                parent = parent.parent
                if not isinstance(parent, Tag):
                    break
                text = parent.get_text(" ", strip=True)
                if 20 <= len(text) <= 1400:
                    if id(parent) not in seen:
                        cards.append(parent)
                        seen.add(id(parent))
                    break

        return cards

    @classmethod
    def _name(cls, card: Tag, query: str | None) -> str | None:
        for selector in cls.NAME_SELECTORS:
            node = card.select_one(selector)
            if node:
                value = node.get_text(" ", strip=True)
                if len(value) >= 3 and "{$" not in value:
                    return value

        lines = [line.strip() for line in card.stripped_strings if len(line.strip()) >= 3]
        ignored = {
            "VER MAS",
            "VER PRODUCTO",
            "AGREGAR",
            "AGREGAR AL CARRITO",
            "PRECIO REGULAR",
            "PRECIO TERCERA EDAD",
            "PRECIO CUARTA EDAD",
            "PRECIO TODO PUBLICO",
            "DESCUENTO / ISV INCLUIDO",
        }
        candidates = []
        for line in lines:
            normalized = normalize_text(line)
            if normalized in ignored:
                continue
            if re.fullmatch(r"L\.?\s*[\d,.]+", line, re.I):
                continue
            candidates.append(line)

        if not candidates:
            return None
        if query:
            return max(candidates, key=lambda value: relevance_score(query, value))
        return candidates[0]

    @staticmethod
    def _preferred_link(card: Tag, page_url: str) -> str:
        links = [node for node in card.find_all("a", href=True) if isinstance(node, Tag)]
        if not links:
            return page_url

        preferred = None
        for node in links:
            href = str(node.get("href") or "")
            lowered = href.lower()
            if any(key in lowered for key in ("/producto/", "/products/", "/detalle/", "/product/")):
                preferred = href
                break
        href = preferred or str(links[0].get("href") or "")
        return urljoin(page_url, href)

    @classmethod
    def parse(
        cls,
        html: str,
        page_url: str,
        pharmacy: str,
        *,
        query: str | None = None,
        allow_missing_price: bool = False,
    ) -> list[Product]:
        if html.count("{$") > 5 and not re.search(r"L\.?\s*\d", html, re.I):
            return []

        soup = BeautifulSoup(html, "html.parser")
        cards = cls._candidate_cards(soup)
        products: list[Product] = []
        seen: set[tuple[str, float | None, str]] = set()

        for card in cards:
            text = card.get_text(" ", strip=True)
            if not text:
                continue

            name = cls._name(card, query)
            if not name:
                continue

            normalized_name = normalize_text(name)
            if query and relevance_score(query, name) < 45:
                continue

            regular = None
            price = None

            public_match = re.search(
                r"PRECIO\s+TODO\s+PUBLICO.*?(L\.?\s*[\d,]+(?:\.\d{1,2})?)",
                normalize_text(text),
                re.I,
            )
            regular_match = re.search(
                r"PRECIO\s+REGULAR.*?(L\.?\s*[\d,]+(?:\.\d{1,2})?)",
                normalize_text(text),
                re.I,
            )

            if public_match:
                price = parse_money(public_match.group(1))
            if regular_match:
                regular = parse_money(regular_match.group(1))

            money_tokens = re.findall(
                r"(?:LPS\.?|L\.?|HNL)\s*\d[\d,]*(?:\.\d{1,2})?",
                text,
                re.I,
            )
            prices = [parse_money(token) for token in money_tokens]
            prices = [value for value in prices if value is not None]

            if price is None and prices:
                price = prices[-1]
            if regular is None and len(prices) >= 2 and price is not None:
                candidates = [value for value in prices[:-1] if value >= price]
                regular = candidates[0] if candidates else None

            if price is None and not allow_missing_price:
                continue

            url = cls._preferred_link(card, page_url)
            lowered = normalize_text(text)
            available = None
            if any(
                word in lowered
                for word in ("AGOTADO", "NO DISPONIBLE", "SIN EXISTENCIA", "SIN INVENTARIO")
            ):
                available = False
            elif any(
                word in lowered
                for word in ("EN STOCK", "DISPONIBLE", "AGREGAR AL CARRITO", "AGREGAR")
            ):
                available = True

            qty = extract_quantity(name)
            key = (normalized_name, price, url)
            if key in seen:
                continue
            seen.add(key)

            products.append(
                Product(
                    pharmacy=pharmacy,
                    name=name,
                    price=price,
                    regular_price=regular,
                    url=url,
                    quantity=qty,
                    concentration=extract_concentration(name),
                    unit_price=(
                        round(price / qty, 2)
                        if price is not None and qty and qty > 1
                        else None
                    ),
                    available=available,
                )
            )

        return products
