from __future__ import annotations

import shutil
from collections.abc import Awaitable, Callable

from playwright.async_api import Browser, Page, async_playwright


class BrowserUnavailable(RuntimeError):
    pass


def _system_browser() -> str | None:
    for name in (
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "brave-browser",
        "brave",
        "microsoft-edge",
    ):
        path = shutil.which(name)
        if path:
            return path
    return None


async def _launch(playwright) -> Browser:
    executable = _system_browser()
    kwargs = {"headless": True}
    if executable:
        kwargs["executable_path"] = executable

    try:
        return await playwright.chromium.launch(**kwargs)
    except Exception as exc:
        raise BrowserUnavailable(
            "No pude iniciar Chromium. Ejecuta: farmahn setup-browser"
        ) from exc


async def rendered_html(
    url: str,
    *,
    interaction: Callable[[Page], Awaitable[None]] | None = None,
    timeout_ms: int = 25000,
    settle_ms: int = 1800,
) -> tuple[str, str]:
    async with async_playwright() as playwright:
        browser = await _launch(playwright)
        try:
            page = await browser.new_page(
                locale="es-HN",
                viewport={"width": 1440, "height": 1000},
            )
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if interaction is not None:
                await interaction(page)

            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            await page.wait_for_timeout(settle_ms)
            return await page.content(), page.url
        finally:
            await browser.close()


async def search_form(
    url: str,
    query: str,
    *,
    placeholders: tuple[str, ...],
    timeout_ms: int = 25000,
) -> tuple[str, str]:
    async def interact(page: Page) -> None:
        locator = None
        for placeholder in placeholders:
            candidate = page.get_by_placeholder(placeholder, exact=False)
            if await candidate.count():
                locator = candidate.first
                break

        if locator is None:
            candidates = page.locator("input[type='search'], input[type='text']")
            count = await candidates.count()
            for index in range(count):
                candidate = candidates.nth(index)
                try:
                    if await candidate.is_visible():
                        locator = candidate
                        break
                except Exception:
                    continue

        if locator is None:
            raise RuntimeError("No se encontró el campo de búsqueda del sitio.")

        await locator.fill(query)
        await locator.press("Enter")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

    return await rendered_html(url, interaction=interact, timeout_ms=timeout_ms)
