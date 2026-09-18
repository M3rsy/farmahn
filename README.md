# 💊 FarmaHN

Comparador CLI de precios y disponibilidad de medicamentos para farmacias de Honduras.

## v0.2

FarmaHN consulta las fuentes configuradas **en paralelo** y combina los resultados en una sola tabla.

### Proveedores

| Farmacia | Estado | Datos objetivo |
|---|---|---|
| Farmacia San Antonio | Estable inicial | nombre, precio, oferta, enlace, disponibilidad HTML |
| Farmacia Simán | Experimental | nombre, precio, enlace; stock por sucursal pendiente de fijar API dinámica |
| Farmacias Kielsa | Experimental | nombre, precio, enlace |
| Farmacias del Ahorro | Experimental | nombre, precio, enlace, disponibilidad cuando el sitio la publique |

Los proveedores experimentales ya participan en cada búsqueda. Si un sitio cambia, bloquea la petición o entrega el catálogo mediante JavaScript/API no identificada, **solo esa fuente falla** y las demás continúan.

## Instalación

```bash
git clone https://github.com/M3rsy/farmahn.git
cd farmahn

python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Para pruebas:

```bash
pip install -e '.[dev]'
pytest -q
```

## Uso

Menú interactivo:

```bash
farmahn
```

Búsqueda directa en todas las farmacias:

```bash
farmahn buscar "paracetamol"
farmahn buscar "metformina 850" --ciudad "San Pedro Sula"
```

Salida estructurada:

```bash
farmahn buscar "paracetamol" --json
```

Estado de integraciones:

```bash
farmahn farmacias
```

## Arquitectura

```text
farmahn/
├── cli/
├── core/
│   ├── models.py
│   ├── normalize.py
│   └── search.py
├── providers/
│   ├── base.py
│   ├── generic_html.py
│   ├── san_antonio.py
│   ├── siman.py
│   ├── kielsa.py
│   ├── ahorro.py
│   └── registry.py
└── utils/
```

Cada farmacia tiene su propio provider. Por eso un cambio de HTML en Kielsa, por ejemplo, no requiere modificar el motor principal.

## Sitios dinámicos

Simán muestra públicamente en su interfaz información de inventario por sucursal, pero carga gran parte de su catálogo dinámicamente. La v0.2 incluye la integración HTTP y detección de páginas no hidratadas; el siguiente paso es fijar el endpoint público exacto que utiliza el navegador para obtener productos y `invActual`.

Kielsa y Farmacias del Ahorro también se mantienen aisladas como providers propios para poder ajustar sus requests sin tocar la aplicación.

## Uso responsable

FarmaHN trabaja con información publicada para usuarios de las farmacias. No intenta evadir CAPTCHA, autenticación ni controles anti-bot. Para despliegues de volumen se deben respetar términos de uso, robots.txt, caché y límites de petición.

## Roadmap

- Confirmar endpoints dinámicos exactos de Simán, Kielsa y Del Ahorro.
- Stock por sucursal.
- SQLite para caché e historial de precios.
- Favoritos y alertas.
- Comparación por presentación y precio unitario.
- API FastAPI y, posteriormente, frontend web/app.
