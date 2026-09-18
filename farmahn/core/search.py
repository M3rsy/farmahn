from __future__ import annotations

import asyncio
from dataclasses import dataclass
from math import inf

from farmahn.core.models import Product
from farmahn.core.normalize import (
    canonical_product_key,
    extract_concentration,
    extract_dosage_form,
    extract_quantity,
    relevance_score,
)
from farmahn.providers.base import PharmacyProvider
from farmahn.storage.db import Database, default_database


@dataclass
class ProviderStatus:
    provider: str
    ok: bool
    count: int = 0
    error: str | None = None
    cached: bool = False


def _price(product: Product) -> float:
    return product.price if product.price is not None else inf


def enrich_product(product: Product, query: str) -> Product:
    quantity = product.quantity or extract_quantity(product.name)
    concentration = product.concentration or extract_concentration(product.name)
    dosage_form = product.dosage_form or extract_dosage_form(product.name)
    canonical_key = product.canonical_key or canonical_product_key(product.name)
    unit_price = product.unit_price

    if (
        unit_price is None
        and product.price is not None
        and quantity
        and quantity > 1
    ):
        unit_price = round(product.price / quantity, 2)

    return product.model_copy(
        update={
            "quantity": quantity,
            "concentration": concentration,
            "dosage_form": dosage_form,
            "canonical_key": canonical_key,
            "unit_price": unit_price,
            "match_score": relevance_score(query, product.name),
        }
    )


def deduplicate(products: list[Product]) -> list[Product]:
    selected: dict[tuple[str, str], Product] = {}
    for product in products:
        key = (
            product.pharmacy.casefold(),
            product.canonical_key or canonical_product_key(product.name),
        )
        current = selected.get(key)
        if current is None:
            selected[key] = product
            continue

        # Si solo uno de los duplicados tiene precio, conservar ese.
        if current.price is None and product.price is not None:
            selected[key] = product
        elif product.price is not None and current.price is not None and product.price < current.price:
            selected[key] = product

    return list(selected.values())


async def search_all(
    providers: list[PharmacyProvider],
    query: str,
    city: str | None = None,
    *,
    use_cache: bool = True,
    cache_ttl: int = 10,
    only_available: bool = False,
    order: str = "precio",
    db: Database | None = None,
):
    database = db or default_database

    async def run(provider: PharmacyProvider):
        if use_cache:
            cached = database.get_cached_search(provider.slug, query, city)
            if cached is not None:
                items = [enrich_product(item, query) for item in cached]
                return items, ProviderStatus(
                    provider.name, True, len(items), cached=True
                )

        try:
            items = await provider.search(query, city=city)
            items = deduplicate([enrich_product(item, query) for item in items])
            database.record_prices(provider.slug, items, city)
            database.set_cached_search(
                provider.slug,
                query,
                city,
                items,
                ttl_minutes=cache_ttl,
            )
            return items, ProviderStatus(provider.name, True, len(items))
        except Exception as exc:
            return [], ProviderStatus(provider.name, False, 0, str(exc))

    batches = await asyncio.gather(*(run(provider) for provider in providers))
    products = deduplicate([item for items, _ in batches for item in items])

    if only_available:
        products = [product for product in products if product.available is True]

    order_key = order.casefold()
    if order_key == "relevancia":
        products.sort(key=lambda p: (-(p.match_score or 0), _price(p)))
    elif order_key == "nombre":
        products.sort(key=lambda p: (p.name.casefold(), _price(p)))
    elif order_key == "farmacia":
        products.sort(key=lambda p: (p.pharmacy.casefold(), _price(p)))
    else:
        products.sort(key=lambda p: (_price(p), -(p.match_score or 0)))

    statuses = [status for _, status in batches]
    return products, statuses


async def health_all(providers: list[PharmacyProvider]):
    return await asyncio.gather(*(provider.healthcheck() for provider in providers))
