import pytest

from farmahn.core.models import Product
from farmahn.core.search import search_all
from farmahn.providers.base import PharmacyProvider
from farmahn.storage.db import Database


class FakeProvider(PharmacyProvider):
    name = "Farmacia de prueba"
    slug = "prueba"
    base_url = "https://example.test/"

    def __init__(self):
        self.calls = 0

    async def search(self, query: str, city: str | None = None):
        self.calls += 1
        return [
            Product(
                pharmacy=self.name,
                name="METFORMINA 850MG X30 TAB",
                price=300.0,
                url="https://example.test/a",
                available=True,
            ),
            Product(
                pharmacy=self.name,
                name="METFORMINA 850 MG X 30 TABLETAS",
                price=310.0,
                url="https://example.test/b",
                available=True,
            ),
        ]


@pytest.mark.asyncio
async def test_search_deduplicates_and_uses_cache(tmp_path):
    provider = FakeProvider()
    db = Database(tmp_path / "farmahn.db")

    first, first_status = await search_all([provider], "metformina 850", db=db)
    second, second_status = await search_all([provider], "metformina 850", db=db)

    assert provider.calls == 1
    assert len(first) == 1
    assert len(second) == 1
    assert first[0].price == 300.0
    assert first_status[0].cached is False
    assert second_status[0].cached is True



class AvailabilityProvider(PharmacyProvider):
    name = "Orden"
    slug = "orden"
    base_url = "https://example.test/"

    async def search(self, query: str, city: str | None = None):
        return [
            Product(
                pharmacy=self.name,
                name="PRODUCTO SIN STOCK",
                price=10.0,
                url="https://example.test/out",
                available=False,
            ),
            Product(
                pharmacy=self.name,
                name="PRODUCTO DESCONOCIDO",
                price=20.0,
                url="https://example.test/unknown",
                available=None,
            ),
            Product(
                pharmacy=self.name,
                name="PRODUCTO DISPONIBLE",
                price=30.0,
                url="https://example.test/in",
                available=True,
            ),
        ]


@pytest.mark.asyncio
async def test_available_products_are_sorted_first(tmp_path):
    db = Database(tmp_path / "sort.db")
    products, _ = await search_all(
        [AvailabilityProvider()],
        "producto",
        db=db,
        use_cache=False,
        order="precio",
    )

    assert [product.available for product in products] == [True, None, False]


class MissingPriceProvider(PharmacyProvider):
    name = "Sin precio"
    slug = "sin-precio"
    base_url = "https://example.test/"

    async def search(self, query: str, city: str | None = None):
        return [
            Product(
                pharmacy=self.name,
                name="GLUCERNA SR VAINILLA 400G",
                price=None,
                url="https://example.test/glucerna",
                available=True,
            )
        ]


@pytest.mark.asyncio
async def test_product_without_price_is_not_discarded(tmp_path):
    db = Database(tmp_path / "missing-price.db")
    products, status = await search_all(
        [MissingPriceProvider()],
        "glucerna",
        db=db,
        use_cache=False,
    )

    assert status[0].ok is True
    assert len(products) == 1
    assert products[0].price is None
    assert db.history("glucerna") == []
