"""`xsight remove` command — permanently removes an indexed repository's
XSight-owned data. Never touches the repository's source files on disk.

Deletion order: vector entries -> parsed modules -> files -> repository row,
so a partial failure never orphans SQLite FK references and re-running the
command remains safe (the repository row is only deleted last).
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from xsight.config.settings import settings
from xsight.database.connection import get_connection
from xsight.database.repositories import delete_repository, get_repository, get_repository_by_id
from xsight.vectorstore.core import delete, list_point_ids
from xsight.vectorstore.provider import QdrantVectorStoreProvider

console = Console()


def run(path: Path = typer.Argument(Path("."))) -> None:
    resolved_path = path.expanduser().resolve()

    conn = get_connection()
    repo_id = get_repository(resolved_path, conn)

    if repo_id is None:
        conn.close()
        console.print("[red]Repository hasn't been indexed. Run [bold]`xsight init`[/bold] first.[/red]")
        return

    row = get_repository_by_id(repo_id, conn)

    console.rule(style="green")
    console.print("[bold cyan]XSight[/bold cyan] [dim]v0.1.0[/dim]", justify="center")
    console.print("[white]AI Repository Assistant[/white]", justify="center")
    console.rule(style="green")
    console.print()

    console.print(
        Panel(
            f"[bold]Name[/bold] : {row['name']}\n[bold]Path[/bold] : {row['path']}",
            title="Repository",
            title_align="left",
            border_style="cyan",
        )
    )
    console.print()
    console.print("[bold yellow]⚠ Warning:[/bold yellow] [yellow]This action is irreversible.[/yellow]\n")
    console.print("The following will be permanently deleted:")
    console.print("  [red]•[/red] Repository metadata")
    console.print("  [red]•[/red] File metadata")
    console.print("  [red]•[/red] Parsed modules")
    console.print("  [red]•[/red] Chunks")
    console.print("  [red]•[/red] Embeddings")
    console.print("  [red]•[/red] Vector database entries")
    console.print()

    confirmed = Confirm.ask(
        "[bold red]Remove this repository from XSight?[/bold red]",
        default=False,
    )

    if not confirmed:
        console.print("[yellow]● Cancelled. No changes were made.[/yellow]")
        conn.close()
        return

    console.print()
    vector_provider = QdrantVectorStoreProvider(
        collection_name=settings.qdrant_collection,
        url=settings.qdrant_url,
    )

    point_ids = list_point_ids(repo_id, vector_provider)
    delete(list(point_ids), vector_provider)
    console.print("[green]✓[/green] Vector entries removed")

    delete_repository(repo_id, conn)
    conn.commit()
    conn.close()
    console.print("[green]✓[/green] Repository metadata removed")

    console.print()
    console.print(
        Panel(
            "[green]Repository removed successfully.[/green]\n"
            "XSight no longer tracks this repository.",
            title="✓ Done",
            title_align="left",
            border_style="green",
        )
    )