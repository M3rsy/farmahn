from farmahn.providers.generic_html import GenericProductParser


def test_kielsa_rendered_card_prefers_public_price():
    html = """
    <div class="product-card">
      <a href="/producto/desitin-57">
        <div class="product-title">DESITIN MAXIMA PROTECCION UNG 57GRS</div>
      </a>
      <div>Precio regular L. 360.15</div>
      <div>Precio tercera edad L. 350.15</div>
      <div>Precio cuarta edad L. 350.15</div>
      <div>Precio todo público L. 350.15</div>
      <a href="/producto/desitin-57">AGREGAR AL CARRITO</a>
    </div>
    """
    items = GenericProductParser.parse(
        html,
        "https://www.kielsa.com/searchproduct/1/TODAS/DESITIN",
        "Farmacias Kielsa",
        query="DESITIN",
    )
    assert len(items) == 1
    assert items[0].price == 350.15
    assert items[0].regular_price == 360.15
    assert items[0].available is True
    assert items[0].url == "https://www.kielsa.com/producto/desitin-57"


def test_ahorro_keeps_search_result_even_when_price_is_hidden():
    html = """
    <div class="card">
      <img src="/desitin.png">
      <div>Desitin Crema Aloe & Vitamina E, tubo 57</div>
      <div>Johnson&Johnson</div>
      <a href="/hn/products/123-desitin-crema-57">VER MÁS</a>
    </div>
    """
    items = GenericProductParser.parse(
        html,
        "https://www.farmaciasdelahorro.hn/hn/products",
        "Farmacias del Ahorro",
        query="DESITIN",
        allow_missing_price=True,
    )
    assert len(items) == 1
    assert items[0].price is None
    assert "desitin" in items[0].name.lower()
    assert items[0].url.endswith("/hn/products/123-desitin-crema-57")
