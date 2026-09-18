from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from farmahn.core.models import Product

console = Console()


def banner():
    title = Text("💊 FARMAHN", style="bold cyan")
    subtitle = "Comparador de medicamentos en Honduras"
    console.print(Panel.fit(Text.assemble(title, "\n", subtitle), border_style="cyan"))


def render_products(products: list[Product]):
    if not products:
        console.print("[yellow]No se encontraron productos.[/yellow]")
        return
    table = Table(title="Resultados", header_style="bold cyan", show_lines=True)
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Farmacia")
    table.add_column("Producto", overflow="fold")
    table.add_column("Precio", justify="right")
    table.add_column("Oferta", justify="right")
    table.add_column("Disponibilidad")
    for i, p in enumerate(products, 1):
        offer = f"Ahorra L {p.savings:,.2f}" if p.savings else "—"
        stock = "✓ Disponible" if p.available is True else "✗ Sin stock" if p.available is False else "No informada"
        table.add_row(str(i), p.pharmacy, p.name, f"L {p.price:,.2f}", offer, stock)
    console.print(table)
    console.print("[dim]Usa 'farmahn buscar \"nombre\" --json' para salida estructurada.[/dim]")
