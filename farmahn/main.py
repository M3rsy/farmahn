from __future__ import annotations

import asyncio
import json
import platform
import sys
import typer
from rich import print
from rich.panel import Panel

from farmahn import __version__
from farmahn.cli.menu import interactive_menu
from farmahn.core.search import health_all, search_all
from farmahn.providers.registry import get_providers
from farmahn.storage.db import default_database
from farmahn.utils.console import (
    banner,
    render_health,
    render_history,
    render_products,
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="FarmaHN — comparador CLI de farmacias de Honduras",
)


@app.callback(invoke_without_command=True)
def root(ctx: typer.Context):
    """Sin subcomando abre el menú interactivo."""
    if ctx.invoked_subcommand is None:
        interactive_menu()


@app.command("buscar")
def buscar(
    query: str = typer.Argument(..., help="Medicamento, marca o principio activo"),
    ciudad: str | None = typer.Option(None, "--ciudad", "-c", help="Ciudad, por ejemplo 'San Pedro Sula'"),
    farmacia: str | None = typer.Option(None, "--farmacia", "-f", help="Consultar solo una farmacia"),
    solo_disponibles: bool = typer.Option(False, "--solo-disponibles", help="Muestra solo productos confirmados disponibles"),
    orden: str = typer.Option("precio", "--orden", help="precio, relevancia, nombre o farmacia"),
    sin_cache: bool = typer.Option(False, "--sin-cache", help="Fuerza consulta web ignorando caché"),
    cache_minutos: int = typer.Option(10, "--cache-minutos", min=1, max=1440, help="Vigencia del caché"),
    json_output: bool = typer.Option(False, "--json", help="Devuelve JSON"),
):
    """Busca un medicamento en las farmacias configuradas."""
    if orden not in {"precio", "relevancia", "nombre", "farmacia"}:
        raise typer.BadParameter("--orden debe ser precio, relevancia, nombre o farmacia")

    providers = get_providers(farmacia)
    if not providers:
        raise typer.BadParameter(f"No existe una farmacia que coincida con: {farmacia}")

    products, statuses = asyncio.run(
        search_all(
            providers,
            query,
            ciudad,
            use_cache=not sin_cache,
            cache_ttl=cache_minutos,
            only_available=solo_disponibles,
            order=orden,
        )
    )

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "query": query,
                    "city": ciudad,
                    "providers": [status.__dict__ for status in statuses],
                    "results": [product.model_dump(mode="json") for product in products],
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        raise typer.Exit()

    banner()
    for status in statuses:
        state = "[green]✓[/green]" if status.ok else "[red]✗[/red]"
        cache = " [cyan](caché)[/cyan]" if status.cached else ""
        suffix = f" — {status.error}" if status.error else ""
        print(f"{state} {status.provider} — {status.count} resultado(s){cache}{suffix}")
    render_products(products)


@app.command("historial")
def historial(
    query: str = typer.Argument(..., help="Nombre o parte del medicamento"),
    limite: int = typer.Option(30, "--limite", "-n", min=1, max=200),
):
    """Muestra precios guardados por búsquedas anteriores."""
    banner()
    render_history(default_database.history(query, limit=limite))


@app.command("estado")
def estado():
    """Comprueba conectividad básica con cada farmacia."""
    banner()
    rows = asyncio.run(health_all(get_providers()))
    render_health(rows)


@app.command("doctor")
def doctor():
    """Diagnóstico local de FarmaHN."""
    stats = default_database.stats()
    banner()
    print(
        Panel.fit(
            "\n".join(
                [
                    f"FarmaHN: {__version__}",
                    f"Python: {sys.version.split()[0]}",
                    f"Sistema: {platform.system()} {platform.release()}",
                    f"Base de datos: {stats['path']}",
                    f"Entradas de caché: {stats['cache_entries']}",
                    f"Observaciones históricas: {stats['history_entries']}",
                    f"Proveedores: {len(get_providers())}",
                ]
            ),
            title="Diagnóstico local",
        )
    )
    print("\n[bold]Conectividad[/bold]")
    render_health(asyncio.run(health_all(get_providers())))


@app.command("cache-limpiar")
def cache_limpiar():
    """Elimina resultados almacenados en caché sin borrar el historial."""
    count = default_database.clear_cache()
    print(f"[green]✓[/green] Se eliminaron {count} entrada(s) de caché.")


@app.command("farmacias")
def farmacias():
    """Muestra todos los proveedores integrados."""
    for provider in get_providers():
        experimental = getattr(provider, "experimental", False)
        badge = "[yellow]EXPERIMENTAL[/yellow]" if experimental else "[green]ESTABLE[/green]"
        stock = "stock" if getattr(provider, "supports_stock", False) else "sin stock detallado"
        print(f"● {provider.name} ({provider.slug}) — {badge} — {stock}")


if __name__ == "__main__":
    app()
