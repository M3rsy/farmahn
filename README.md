# 💊 FarmaHN

FarmaHN es un comparador CLI/TUI de precios y disponibilidad de medicamentos para farmacias de Honduras.

## v0.3.0

La versión 0.3 incorpora una base local SQLite, caché, historial de precios, normalización de medicamentos, deduplicación, filtros y diagnóstico de proveedores.

### Farmacias

| Farmacia | Estado | Situación actual |
|---|---|---|
| Farmacia San Antonio | Estable inicial | búsqueda HTML, precio, oferta, enlace y detección de agotado cuando el sitio lo publica |
| Farmacia Simán | Experimental | búsqueda preparada; el stock por sucursal depende de confirmar su API dinámica |
| Farmacias Kielsa | Experimental | búsqueda HTML preparada |
| Farmacias del Ahorro | Experimental | búsqueda HTML preparada |

Los cuatro providers participan de forma independiente. Si una farmacia falla, las demás continúan.

## Instalación

```bash
git clone https://github.com/M3rsy/farmahn.git
cd farmahn

python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Para desarrollo:

```bash
pip install -e '.[dev]'
pytest -q
```

## Menú interactivo

```bash
farmahn
```

Incluye:

- Buscar medicamento.
- Buscar solo productos con disponibilidad confirmada.
- Consultar historial.
- Revisar estado de farmacias.
- Elegir una farmacia específica.
- Abrir el enlace directo del producto.

## Búsquedas

Todas las farmacias:

```bash
farmahn buscar "metformina 850"
```

Por ciudad:

```bash
farmahn buscar "metformina 850" --ciudad "San Pedro Sula"
```

Solo una farmacia:

```bash
farmahn buscar "paracetamol" --farmacia kielsa
farmahn buscar "paracetamol" --farmacia siman
farmahn buscar "paracetamol" --farmacia san-antonio
```

Solo disponibilidad confirmada:

```bash
farmahn buscar "paracetamol" --solo-disponibles
```

Orden:

```bash
farmahn buscar "losartan" --orden precio
farmahn buscar "losartan" --orden relevancia
farmahn buscar "losartan" --orden nombre
farmahn buscar "losartan" --orden farmacia
```

Ignorar caché:

```bash
farmahn buscar "metformina" --sin-cache
```

Cambiar duración del caché:

```bash
farmahn buscar "metformina" --cache-minutos 30
```

JSON:

```bash
farmahn buscar "metformina" --json
```

## SQLite e historial

La base de datos se crea automáticamente siguiendo XDG:

```text
~/.local/share/farmahn/farmahn.db
```

o `$XDG_DATA_HOME/farmahn/farmahn.db` cuando esa variable existe.

Se almacenan:

- resultados recientes en caché;
- precios observados;
- farmacia;
- nombre del producto;
- concentración;
- presentación;
- cantidad;
- disponibilidad;
- URL;
- ciudad;
- fecha de observación.

Consultar historial:

```bash
farmahn historial "metformina 850"
```

Limpiar solamente el caché:

```bash
farmahn cache-limpiar
```

El historial no se elimina con ese comando.

## Normalización y comparación

FarmaHN intenta extraer automáticamente:

```text
METFORMINA 850MG X30 TABLETAS

concentración -> 850 mg
cantidad      -> 30
forma         -> tableta
precio unidad -> precio / 30
```

La clave canónica incluye concentración, forma farmacéutica y cantidad. Esto reduce el riesgo de agrupar por error:

```text
Metformina 500 mg x30
Metformina 850 mg x30
Metformina 850 mg x60
```

como si fueran el mismo producto.

También usa RapidFuzz para calcular relevancia respecto de la búsqueda.

## Diagnóstico

Estado HTTP de las farmacias:

```bash
farmahn estado
```

Diagnóstico completo:

```bash
farmahn doctor
```

Muestra:

- versión FarmaHN;
- versión Python;
- sistema operativo;
- ruta SQLite;
- cantidad de elementos en caché;
- número de observaciones históricas;
- estado y latencia de proveedores.

## Arquitectura

```text
farmahn/
├── cli/
│   └── menu.py
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
├── storage/
│   └── db.py
└── utils/
    └── console.py
```

## Caché

El caché se guarda por:

```text
farmacia + consulta + ciudad
```

Por defecto dura 10 minutos. Esto reduce peticiones repetitivas contra los sitios de las farmacias.

Una consulta indica cuando provino del caché:

```text
✓ Farmacia San Antonio — 5 resultado(s) (caché)
```

## Stock por sucursal

El modelo ya soporta:

```text
farmacia
sucursal
ciudad
cantidad
disponible
```

Sin embargo, cantidad real por sucursal solo debe mostrarse cuando el sitio fuente la entregue de forma verificable. Simán carga inventario dinámicamente, por lo que falta fijar el endpoint público exacto antes de considerar esa integración estable.

FarmaHN no inventa cantidades cuando la farmacia no las publica.

## Pruebas

Hay pruebas para:

- parser de San Antonio;
- concentración, cantidad y forma farmacéutica;
- clave canónica;
- relevancia;
- SQLite;
- historial;
- caché;
- deduplicación;
- reutilización de caché.

GitHub Actions ejecuta las pruebas en cada push.

## Uso responsable

FarmaHN consulta información pública de los sitios. No evade autenticación, CAPTCHA ni controles anti-bot. Para despliegues de mayor volumen deben respetarse términos de servicio, robots.txt y límites razonables de petición.

## Próximos objetivos

- Fijar APIs dinámicas reales de Simán, Kielsa y Del Ahorro.
- Stock real por sucursal cuando la fuente lo permita.
- Favoritos.
- Alertas de precio.
- Configuración TOML persistente.
- Exportación CSV.
- API FastAPI.
- Interfaz Textual avanzada.
