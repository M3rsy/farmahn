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
