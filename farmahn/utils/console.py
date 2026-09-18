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
    table.add_column("Unidad", justify="right")
    table.add_column("Oferta", justify="right")
    table.add_column("Disponibilidad")

    for i, product in enumerate(products, 1):
        offer = f"Ahorra L {product.savings:,.2f}" if product.savings else "—"
        if product.available is True:
            stock = "[bold green]✓ Disponible[/bold green]"
        elif product.available is False:
            stock = "[bold red]✗ Sin stock[/bold red]"
        else:
            stock = "[yellow]• No informada[/yellow]"

        price = f"L {product.price:,.2f}" if product.price is not None else "No mostrado"
        unit = f"L {product.unit_price:,.2f}" if product.unit_price is not None else "—"

        table.add_row(
            str(i),
            product.pharmacy,
            product.name,
            price,
            unit,
            offer,
            stock,
        )

    console.print(table)


def render_history(rows: list[dict]):
    if not rows:
        console.print("[yellow]No hay observaciones históricas para esa búsqueda.[/yellow]")
        return

    table = Table(title="Historial de precios", header_style="bold cyan", show_lines=False)
    table.add_column("Fecha")
    table.add_column("Farmacia")
    table.add_column("Producto", overflow="fold")
    table.add_column("Precio", justify="right")
    table.add_column("Ciudad")
    table.add_column("Estado")

    for row in rows:
        available = row.get("available")
        state = (
            "[green]✓ Disponible[/green]"
            if available is True
            else "[red]✗ Sin stock[/red]"
            if available is False
            else "[yellow]• No informada[/yellow]"
        )
        observed = str(row["observed_at"]).replace("T", " ")[:19]
        table.add_row(
            observed,
            row["pharmacy"],
            row["product_name"],
            f"L {row['price']:,.2f}",
            row.get("city") or "—",
            state,
        )
    console.print(table)


def render_health(rows: list[dict]):
    table = Table(title="Estado de proveedores", header_style="bold cyan")
    table.add_column("Farmacia")
    table.add_column("Estado")
    table.add_column("HTTP", justify="right")
    table.add_column("Latencia", justify="right")
    table.add_column("Detalle")

    for row in rows:
        state = "[green]Online[/green]" if row["ok"] else "[red]Error[/red]"
        code = str(row["status_code"]) if row.get("status_code") is not None else "—"
        latency = f"{row['latency_ms']:.0f} ms" if row.get("latency_ms") is not None else "—"
        table.add_row(
            row["provider"],
            state,
            code,
            latency,
            row.get("error") or "",
        )
    console.print(table)
