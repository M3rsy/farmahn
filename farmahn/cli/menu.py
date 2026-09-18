from __future__ import annotations

import asyncio
import webbrowser

from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from farmahn import __version__
from farmahn.core.search import health_all, search_all
from farmahn.providers.registry import get_providers
from farmahn.storage.db import default_database
from farmahn.utils.console import (
    banner,
    console,
    render_health,
    render_history,
    render_products,
)

MENU = {
    "1": "🔎 Buscar medicamento",
    "2": "📦 Buscar solo disponibilidad confirmada",
    "3": "📊 Historial de precios",
    "4": "🌐 Estado de farmacias",
    "5": "🏥 Ver farmacias integradas",
    "6": "ℹ️  Acerca de",
    "0": "❌ Salir",
}


def interactive_menu():
    while True:
        console.clear()
        banner()
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="bold cyan", width=4)
        table.add_column()
        for key, label in MENU.items():
            table.add_row(f"[{key}]", label)
        console.print(table)

        choice = Prompt.ask("[bold]Seleccione una opción[/bold]", choices=list(MENU), default="1")
        if choice == "0":
            console.print("[cyan]Hasta luego.[/cyan]")
            break
        if choice == "1":
            _search_flow()
        elif choice == "2":
            _search_flow(only_available=True)
        elif choice == "3":
            _history_flow()
        elif choice == "4":
            _health_flow()
        elif choice == "5":
            _providers()
        else:
            console.print(
                Panel(
                    f"FarmaHN v{__version__}\n"
                    "Comparador CLI con caché, historial, filtros y providers independientes."
                )
            )
            Prompt.ask("ENTER para volver", default="")


def _providers():
    console.print("\n[bold]Integraciones[/bold]")
    for provider in get_providers():
        experimental = getattr(provider, "experimental", False)
        state = "[yellow]◐[/yellow] experimental" if experimental else "[green]●[/green] estable"
        console.print(f"{state} — {provider.name}")
    Prompt.ask("\nENTER para volver", default="")


def _health_flow():
    with console.status("[bold cyan]Comprobando conectividad...[/bold cyan]"):
        rows = asyncio.run(health_all(get_providers()))
    render_health(rows)
    Prompt.ask("\nENTER para volver", default="")


def _history_flow():
    query = Prompt.ask("[bold cyan]Medicamento para consultar historial[/bold cyan]").strip()
    if query:
        render_history(default_database.history(query, limit=50))
    Prompt.ask("\nENTER para volver", default="")


def _search_flow(only_available: bool = False):
    query = Prompt.ask("[bold cyan]Nombre, marca o principio activo[/bold cyan]").strip()
    if not query:
        return

    console.print("\n[bold]Ciudad[/bold]")
    console.print("1. San Pedro Sula\n2. Tegucigalpa\n3. La Ceiba\n4. Todas")
    city_choice = Prompt.ask("Seleccione", choices=["1", "2", "3", "4"], default="1")
    city_map = {"1": "San Pedro Sula", "2": "Tegucigalpa", "3": "La Ceiba", "4": None}
    city = city_map[city_choice]

    console.print("\n[bold]Farmacia[/bold]")
    console.print("1. Todas\n2. San Antonio\n3. Simán\n4. Kielsa\n5. Del Ahorro")
    pharmacy_choice = Prompt.ask("Seleccione", choices=["1", "2", "3", "4", "5"], default="1")
    pharmacy_map = {
        "1": None,
        "2": "san-antonio",
        "3": "siman",
        "4": "kielsa",
        "5": "ahorro",
    }
    providers = get_providers(pharmacy_map[pharmacy_choice])

    with console.status("[bold cyan]Consultando farmacias en paralelo...[/bold cyan]"):
        products, statuses = asyncio.run(
            search_all(
                providers,
                query,
                city,
                only_available=only_available,
                order="precio",
            )
        )

    console.print()
    for status in statuses:
        icon = "[green]✓[/green]" if status.ok else "[red]✗[/red]"
        cache = " [cyan](caché)[/cyan]" if status.cached else ""
        detail = f" — {status.error}" if status.error else ""
        console.print(f"{icon} {status.provider}: {status.count} resultado(s){cache}{detail}")

    render_products(products)
    if not products:
        Prompt.ask("\nENTER para volver", default="")
        return

    console.print("\n[bold]Acciones[/bold]\n1. Abrir producto\n2. Nueva búsqueda\n0. Volver al menú")
    action = Prompt.ask("Seleccione", choices=["1", "2", "0"], default="0")
    if action == "1":
        idx = IntPrompt.ask("Número del resultado", default=1)
        try:
            product = products[idx - 1]
            webbrowser.open(product.url)
            console.print(f"[green]Abriendo:[/green] {product.url}")
        except IndexError:
            console.print("[red]Número inválido.[/red]")
        Prompt.ask("\nENTER para continuar", default="")
    elif action == "2":
        _search_flow(only_available=only_available)
