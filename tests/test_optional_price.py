from farmahn.core.models import Product
from farmahn.core.search import deduplicate


def test_known_price_wins_over_unknown_duplicate():
    unknown = Product(
        pharmacy="Farmacia X",
        name="DESITIN 57G",
        price=None,
        url="https://example.test/a",
        canonical_key="DESITIN|57 g",
    )
    known = Product(
        pharmacy="Farmacia X",
        name="DESITIN 57G",
        price=300.0,
        url="https://example.test/b",
        canonical_key="DESITIN|57 g",
    )
    result = deduplicate([unknown, known])
    assert len(result) == 1
    assert result[0].price == 300.0
