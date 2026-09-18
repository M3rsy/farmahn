from farmahn.core.models import Product
from farmahn.providers.ahorro import AhorroProvider


def test_ahorro_detail_parses_total_isv_and_cart_availability():
    html = """
    <html>
      <body>
        <h1>Glucerna SR Vainilla, Lata 400gr</h1>
        <button>AGREGAR AL CARRITO</button>
        <div>Total + ISV (L.)</div>
        <div>745.50</div>
      </body>
    </html>
    """
    base = Product(
        pharmacy="Farmacias del Ahorro",
        name="Glucerna SR Vainilla, Lata 400gr",
        price=None,
        url="https://www.farmaciasdelahorro.hn/hn/products/glucerna",
    )

    item = AhorroProvider._parse_detail(html, base.url, base)

    assert item.price == 745.50
    assert item.available is True
    assert "Glucerna" in item.name
