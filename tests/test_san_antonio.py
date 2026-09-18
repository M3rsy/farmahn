from pathlib import Path
from farmahn.providers.san_antonio import SanAntonioProvider


def test_parse_search_html():
    html = Path("tests/fixtures/san_antonio.html").read_text()
    rows = SanAntonioProvider.parse_search_html(html, "https://www.farmaciasanantonio.hn/Buscar/")
    assert len(rows) == 2
    assert rows[0].name == "UNIDAD MK PARACETAMOL 750MG X 100 TAB"
    assert rows[0].price == 3.82
    assert rows[0].regular_price == 4.20
    assert rows[0].quantity == 100
    assert rows[0].unit_price == 0.04
    assert rows[1].url == "https://www.farmaciasanantonio.hn/producto/acetaminofen-500/"
