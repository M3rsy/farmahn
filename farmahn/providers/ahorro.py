from __future__ import annotations

import asyncio
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import Page

from farmahn.core.models import Product
from farmahn.core.normalize import normalize_text, parse_money, relevance_score
from farmahn.providers.base import PharmacyProvider, ProviderError
from farmahn.providers.browser import BrowserUnavailable, rendered_html
from farmahn.providers.generic_html import GenericProductParser


class AhorroProvider(PharmacyProvider):
    name = "Farmacias del Ahorro"
    slug = "ahorro"
    base_url = "https://www.farmaciasdelahorro.hn/"
    experimental = True

    def __init__(self, timeout: float = 25.0):
        self.timeout = timeout

    @staticmethod
    async def _has_results(page: Page, query: str) -> bool:
        try:
            body = normalize_text(await page.locator("body").inner_text())
        except Exception:
            return False

        query_norm = normalize_text(query)
        return (
            "RESULTADOS DE BUSQUEDA" in body
            and query_norm in body
            and ("VER MAS" in body or "AGREGAR AL CARRITO" in body)
        )

    @classmethod
    async def _submit_search(cls, page: Page, query: str) -> None:
        locator = None
        selectors = (
            "input[type='search']",
            "input[placeholder*='medicamento' i]",
            "input[placeholder*='buscar' i]",
            "input[type='text']",
        )

        for selector in selectors:
            candidates = page.locator(selector)
            for index in range(await candidates.count()):
                candidate = candidates.nth(index)
                try:
                    if await candidate.is_visible():
                        locator = candidate
                        break
                except Exception:
                    continue
            if locator is not None:
                break

        if locator is None:
            raise RuntimeError("No se encontró el buscador de Farmacias del Ahorro.")

        await locator.fill(query)
        await locator.focus()

        # Primer intento: ENTER. Algunas versiones del sitio sí envían el
        # formulario así.
        await locator.press("Enter")
        await page.wait_for_timeout(1400)
        if await cls._has_results(page, query):
            return

        # Segundo intento: localizar el botón/icono más cercano a la derecha
        # del input. La web actual usa un icono verde de búsqueda.
        input_box = await locator.bounding_box()
        best = None
        best_distance = None
        candidates = page.locator("button, [role='button'], a")
        for index in range(await candidates.count()):
            candidate = candidates.nth(index)
            try:
                if not await candidate.is_visible():
                    continue
                box = await candidate.bounding_box()
                if not box or not input_box:
                    continue

                vertical_distance = abs(
                    (box["y"] + box["height"] / 2)
                    - (input_box["y"] + input_box["height"] / 2)
                )
                horizontal_distance = box["x"] - (input_box["x"] + input_box["width"])

                if vertical_distance <= 70 and -20 <= horizontal_distance <= 180:
                    distance = abs(horizontal_distance) + vertical_distance
                    if best is None or distance < best_distance:
                        best = candidate
                        best_distance = distance
            except Exception:
                continue

        if best is not None:
            try:
                await best.click()
                await page.wait_for_timeout(1800)
            except Exception:
                pass

        # Tercer intento: disparar submit desde el formulario contenedor si
        # existe. Esto cubre cambios menores del frontend.
        if not await cls._has_results(page, query):
            try:
                form = locator.locator("xpath=ancestor::form[1]")
                if await form.count():
                    await form.evaluate(
                        """form => {
                            if (form.requestSubmit) form.requestSubmit();
                            else form.submit();
                        }"""
                    )
                    await page.wait_for_timeout(1800)
            except Exception:
                pass

        # Esperamos un poco más porque el resultado se llena por JavaScript.
        for _ in range(12):
            if await cls._has_results(page, query):
                return
            await page.wait_for_timeout(500)

        raise RuntimeError(
            "El sitio no cambió a la vista de resultados después de enviar la búsqueda."
        )

    @staticmethod
    def _parse_detail(html: str, url: str, product: Product) -> Product:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        normalized = normalize_text(text)

        price = product.price
        regular_price = product.regular_price

        # La ficha actual muestra: "Total + ISV (L.) 745.50".
        total_match = re.search(
            r"TOTAL\s*\+\s*ISV\s*\(\s*L\.?\s*\)\s*([\d,]+(?:\.\d{1,2})?)",
            text,
            re.I,
        )
        if total_match is None:
            total_match = re.search(
                r"TOTAL\s*\+\s*ISV\s+L\.?\s*([\d,]+(?:\.\d{1,2})?)",
                normalized,
                re.I,
            )
        if total_match:
            price = parse_money(total_match.group(1))

        if price is None:
            # Fallback para cambios menores del texto de precio.
            money = re.findall(
                r"(?:LPS\.?|L\.?|HNL)\s*\d[\d,]*(?:\.\d{1,2})?",
                text,
                re.I,
            )
            values = [parse_money(value) for value in money]
            values = [value for value in values if value is not None]
            if values:
                price = values[-1]

        available = product.available
        if any(
            token in normalized
            for token in ("NO DISPONIBLE", "AGOTADO", "SIN EXISTENCIA", "SIN INVENTARIO")
        ):
            available = False
        elif "AGREGAR AL CARRITO" in normalized:
            available = True

        title = product.name
        for selector in ("h1", "h2", "h3"):
            node = soup.select_one(selector)
            if node:
                candidate = node.get_text(" ", strip=True)
                if relevance_score(product.name, candidate) >= 45:
                    title = candidate
                    break

        return product.model_copy(
            update={
                "name": title,
                "price": price,
                "regular_price": regular_price,
                "available": available,
                "url": url,
            }
        )

    async def _enrich_details(self, products: list[Product]) -> list[Product]:
        async def enrich(product: Product) -> Product:
            if product.url.rstrip("/") == self.base_url.rstrip("/"):
                return product

            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) FarmaHN/0.3.2",
                        "Accept-Language": "es-HN,es;q=0.9",
                    },
                ) as client:
                    response = await client.get(product.url)
                    response.raise_for_status()
                    enriched = self._parse_detail(
                        response.text,
                        str(response.url),
                        product,
                    )
                    if enriched.price is not None:
                        return enriched
            except Exception:
                pass

            # Si el detalle también es dinámico, ejecutamos JavaScript solo para
            # los productos que todavía no tienen precio/disponibilidad clara.
            if product.price is None or product.available is None:
                try:
                    html, final_url = await rendered_html(product.url, settle_ms=1200)
                    return self._parse_detail(html, final_url, product)
                except Exception:
                    return product

            return product

        # Limitar la expansión evita abrir demasiadas páginas si una búsqueda es
        # muy amplia. Las coincidencias más relevantes van primero.
        limited = sorted(
            products,
            key=lambda product: -relevance_score(product.name, product.name),
        )[:10]
        enriched = await asyncio.gather(*(enrich(product) for product in limited))

        if len(products) > len(limited):
            enriched.extend(products[len(limited):])
        return enriched

    async def search(self, query: str, city: str | None = None):
        try:
            html, final_url = await rendered_html(
                self.base_url,
                interaction=lambda page: self._submit_search(page, query),
                timeout_ms=30000,
                settle_ms=1500,
            )
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
        if not items:
            raise ProviderError(
                "Farmacias del Ahorro mostró resultados en el navegador, pero "
                "FarmaHN no pudo identificar las tarjetas de productos."
            )

        items.sort(key=lambda product: -relevance_score(query, product.name))
        return await self._enrich_details(items)
