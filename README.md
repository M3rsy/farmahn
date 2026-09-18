# 💊 FarmaHN

MVP de un comparador CLI de medicamentos para farmacias de Honduras.

## Características de v0.1

- Menú interactivo bonito (`farmahn`).
- Comando directo (`farmahn buscar "paracetamol"`).
- Salida JSON para futuras API/web (`--json`).
- Arquitectura desacoplada por farmacia.
- Integración inicial de Farmacia San Antonio.
- Captura de nombre, precio, precio regular/oferta, presentación aproximada y enlace directo cuando el HTML lo expone.
- Fallos aislados: una farmacia caída no tumba toda la consulta.
- Simán, Kielsa y Farmacias del Ahorro quedan como proveedores preparados para la siguiente iteración.

## Instalación en Linux

```bash
git clone https://github.com/M3rsy/farmahn.git
cd farmahn
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Opcional para pruebas:

```bash
pip install -e '.[dev]'
pytest -q
```

## Uso

Menú interactivo:

```bash
farmahn
```

Búsqueda directa:

```bash
farmahn buscar "paracetamol"
farmahn buscar "metformina 850" --ciudad "San Pedro Sula"
farmahn buscar "paracetamol" --json
```

Ver farmacias:

```bash
farmahn farmacias
```

## Nota sobre sitios externos

FarmaHN consulta únicamente información que los sitios de las farmacias publican para sus usuarios. Los sitios pueden cambiar su HTML, rutas o políticas en cualquier momento. No se incluyen técnicas para evadir CAPTCHA, autenticación o controles anti-bot. Antes de desplegar consultas automatizadas de alto volumen se deben revisar los términos y robots.txt de cada proveedor y configurar caché/rate limiting.

## Estado del proveedor San Antonio

La tienda pública de Farmacia San Antonio expone catálogo, precios y enlaces de productos. El código intenta varias formas comunes de enviar la búsqueda a `/Buscar/` y a WordPress/WooCommerce y luego normaliza el HTML recibido. La lógica del parser está cubierta con pruebas locales; la conectividad real depende de la red y de la forma actual del sitio.

## Próximos pasos

1. Confirmar en navegador/DevTools el request exacto del buscador San Antonio y fijar un único endpoint.
2. Analizar requests públicos de Simán para precio/stock por sucursal.
3. Integrar Kielsa y Farmacias del Ahorro.
4. Añadir SQLite (caché, historial, favoritos).
5. Añadir comparación por presentación/unidad.
6. Migrar opcionalmente la interfaz interactiva a Textual.
