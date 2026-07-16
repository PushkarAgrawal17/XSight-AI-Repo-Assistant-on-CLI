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
        console.print("[dim]Repository is not indexed.[/dim]")
        return

    row = get_repository_by_id(repo_id, conn)

    console.rule("[bold cyan]Remove Repository[/bold cyan]")
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
    console.print("[bold yellow]Warning:[/bold yellow] This action is irreversible.\n")
    console.print("  • Repository metadata")
    console.print("  • File metadata")
    console.print("  • Parsed modules")
    console.print("  • Chunks")
    console.print("  • Embeddings")
    console.print("  • Vector database entries")
    console.print()

    confirmed = typer.confirm(
        "Remove this repository from XSight?",
        default=False,
    )
    if not confirmed:
        conn.close()
        console.print("[dim]Cancelled.[/dim]")
        return

    console.print()
    vector_provider = QdrantVectorStoreProvider(
        collection_name=settings.qdrant_collection,
        url=settings.qdrant_url,
    )

    console.print("[dim]Removing vector entries...[/dim]")
    point_ids = list_point_ids(repo_id, vector_provider)
    delete(list(point_ids), vector_provider)

    console.print("[dim]Removing repository metadata...[/dim]")
    delete_repository(repo_id, conn)
    conn.commit()
    conn.close()

    console.print()
    console.print("[bold green]✓[/bold green] Repository removed successfully.")
    console.print("[dim]XSight no longer tracks this repository.[/dim]")