"""`xsight repos` command — lists every indexed repository.

Purely a database read: the repository catalog, not a single repository's
contents. Never scans the filesystem, never loads the graph, never touches
embeddings/vectorstore/LLM. Follows the visual style established in help.py.
"""

from datetime import datetime

from rich import box
from rich.console import Console
from rich.table import Table

from xsight.database.connection import get_connection
from xsight.database.repositories import list_repositories

console = Console()


def _format_timestamp(raw: str | None) -> str:
    if not raw:
        return "[dim]never[/dim]"
    try:
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw


def run() -> None:
    conn = get_connection()
    rows = list_repositories(conn)
    conn.close()

    console.rule("[bold cyan]Indexed Repositories[/bold cyan]")
    console.print()

    if not rows:
        console.print("[dim]No indexed repositories found.[/dim]")
        console.print()
        console.print("Run [bold green]xsight init <path>[/bold green] to index your first repository.")
        console.print()
        return

    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=box.SIMPLE_HEAVY,
        padding=(0, 2, 0, 2),
        expand=False,
    )
    table.add_column("#", style="dim", no_wrap=True)
    table.add_column("Repository", style="bold green", no_wrap=True)
    table.add_column("Path", style="default", overflow="ellipsis", max_width=60)
    table.add_column("Last Indexed", style="dim", no_wrap=True)

    for i, row in enumerate(rows, start=1):
        table.add_row(str(i), row["name"], row["path"], _format_timestamp(row["last_indexed_at"]))

    console.print(table)
    console.print()
    console.print(f"[dim]Total repositories: {len(rows)}[/dim]")
    console.print()