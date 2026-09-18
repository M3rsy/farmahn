from __future__ import annotations

import asyncio
import webbrowser
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table

from farmahn.core.search import search_all
from farmahn.providers.registry import get_providers
from farmahn.utils.console import console, banner, render_products

MENU = {
    "1": "🔎 Buscar medicamento",
    "2": "📦 Consultar existencia",
    "3": "🏥 Ver farmacias integradas",
    "4": "ℹ️  Acerca de",
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
            _search_flow(stock_focus=True)
        elif choice == "3":
            _providers()
        else:
            console.print(Panel("FarmaHN v0.1.0\nCLI extensible para consultar precios públicos de farmacias hondureñas."))
            Prompt.ask("ENTER para volver", default="")


def _providers():
    console.print("\n[bold]Integraciones[/bold]")
    console.print("[green]●[/green] Farmacia San Antonio — activa")
    console.print("[yellow]○[/yellow] Farmacia Simán — preparada")
    console.print("[yellow]○[/yellow] Farmacias Kielsa — preparada")
    console.print("[yellow]○[/yellow] Farmacias del Ahorro — preparada")
    Prompt.ask("\nENTER para volver", default="")


def _search_flow(stock_focus: bool = False):
    query = Prompt.ask("[bold cyan]Nombre, marca o principio activo[/bold cyan]").strip()
    if not query:
        return
    console.print("\n[bold]Ciudad[/bold]")
    console.print("1. San Pedro Sula\n2. Tegucigalpa\n3. La Ceiba\n4. Todas")
    city_choice = Prompt.ask("Seleccione", choices=["1", "2", "3", "4"], default="1")
    city_map = {"1": "San Pedro Sula", "2": "Tegucigalpa", "3": "La Ceiba", "4": None}
    city_arg = city_map[city_choice]

    with console.status("[bold cyan]Consultando farmacias...[/bold cyan]"):
        products, statuses = asyncio.run(search_all(get_providers(), query, city_arg))
    console.print()
    for s in statuses:
        icon = "[green]✓[/green]" if s.ok else "[red]✗[/red]"
        console.print(f"{icon} {s.provider}: {s.count} resultado(s)" + (f" — {s.error}" if s.error else ""))
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
        _search_flow(stock_focus=stock_focus)
