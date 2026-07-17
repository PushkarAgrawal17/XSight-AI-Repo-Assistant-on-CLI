from datetime import datetime

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from xsight.database.connection import get_connection
from xsight.database.repositories import list_repositories

console = Console()


def _format_timestamp(raw: str | None) -> str:
    if not raw:
        return "Never"

    try:
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw


def run() -> None:
    conn = get_connection()
    rows = list_repositories(conn)
    conn.close()

    console.rule(style="green")
    console.print(
        "[bold cyan]XSight[/bold cyan] [dim]v0.1.0[/dim]",
        justify="center",
    )
    console.print(
        "[white]AI Repository Assistant[/white]",
        justify="center",
    )
    console.rule(style="green")
    console.print()

    if not rows:
        console.print(
            Panel(
                "No indexed repositories were found.\n\n"
                "Run [bold]xsight init <path>[/bold] to index your first repository.",
                title="[bold cyan]📦 Repository Catalog[/bold cyan]",
                title_align="left",
                border_style="yellow",
            )
        )
        return

    console.print("[bold cyan]📦 Repository Catalog[/bold cyan]")
    console.print()

    table = Table(
        box=box.MINIMAL_HEAVY_HEAD,
        show_header=True,
        header_style="bold cyan",
        padding=(0, 2),
        expand=False,
    )

    table.add_column("#", justify="right", no_wrap=True)
    table.add_column("Repository", style="bold green", no_wrap=True)
    table.add_column("Path")
    table.add_column("Last Indexed", no_wrap=True)

    for index, row in enumerate(rows, start=1):
        table.add_row(
            str(index),
            row["name"],
            row["path"],
            _format_timestamp(row["last_indexed_at"]),
        )

    console.print(table)
    console.print()

    console.print(
        Panel(
            f"[bold green]{len(rows)}[/bold green] repositories currently indexed.",
            title="[bold green]✓ Summary[/bold green]",
            title_align="left",
            border_style="green",
        )
    )