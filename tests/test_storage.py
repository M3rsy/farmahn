from farmahn.core.models import Product
from farmahn.storage.db import Database


def test_cache_roundtrip(tmp_path):
    db = Database(tmp_path / "farmahn.db")
    products = [
        Product(
            pharmacy="Prueba",
            name="METFORMINA 850MG X30 TAB",
            price=300.0,
            url="https://example.test/metformina",
        )
    ]
    db.set_cached_search("prueba", "metformina 850", "San Pedro Sula", products, ttl_minutes=10)

    cached = db.get_cached_search("prueba", "metformina 850", "San Pedro Sula")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].price == 300.0


def test_history_roundtrip(tmp_path):
    db = Database(tmp_path / "farmahn.db")
    products = [
        Product(
            pharmacy="Prueba",
            name="LOSARTAN 100MG X30 TAB",
            price=250.0,
            url="https://example.test/losartan",
            concentration="100 mg",
            quantity=30,
            canonical_key="LOSARTAN|100 mg|tableta|30",
        )
    ]
    db.record_prices("prueba", products, "San Pedro Sula")
    rows = db.history("losartan 100")
    assert len(rows) == 1
    assert rows[0]["price"] == 250.0
    assert rows[0]["city"] == "San Pedro Sula"
