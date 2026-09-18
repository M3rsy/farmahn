from __future__ import annotations

import asyncio
import json
import typer
from rich import print

from farmahn.cli.menu import interactive_menu
from farmahn.core.search import search_all
from farmahn.providers.registry import get_providers
from farmahn.utils.console import banner, render_products

app = typer.Typer(add_completion=False, no_args_is_help=False, help="FarmaHN — comparador CLI de farmacias de Honduras")


@app.callback(invoke_without_command=True)
def root(ctx: typer.Context):
    """Sin subcomando abre el menú interactivo."""
    if ctx.invoked_subcommand is None:
        interactive_menu()


@app.command("buscar")
def buscar(
    query: str = typer.Argument(..., help="Medicamento, marca o principio activo"),
    ciudad: str | None = typer.Option(None, "--ciudad", "-c", help="Ciudad, por ejemplo 'San Pedro Sula'"),
    json_output: bool = typer.Option(False, "--json", help="Devuelve JSON"),
):
    """Busca un medicamento directamente desde la terminal."""
    products, statuses = asyncio.run(search_all(get_providers(), query, ciudad))
    if json_output:
        typer.echo(json.dumps({
            "query": query,
            "city": ciudad,
            "providers": [s.__dict__ for s in statuses],
            "results": [p.model_dump(mode="json") for p in products],
        }, ensure_ascii=False, indent=2, default=str))
        raise typer.Exit()
    banner()
    for s in statuses:
        state = "[green]✓[/green]" if s.ok else "[red]✗[/red]"
        print(f"{state} {s.provider} — {s.count} resultado(s)")
    render_products(products)


@app.command("farmacias")
def farmacias():
    """Muestra proveedores activos y planificados."""
    for p in get_providers(active_only=False):
        active = p.slug == "san-antonio"
        print(f"{'[green]●[/green]' if active else '[yellow]○[/yellow]'} {p.name} ({p.slug})")


if __name__ == "__main__":
    app()
