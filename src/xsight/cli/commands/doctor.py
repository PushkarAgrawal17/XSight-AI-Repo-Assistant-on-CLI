"""`xsight doctor` command — read-only diagnostics.

Never calls sync(), run_pipeline(), load_repo_graph(), embeddings, chunking,
or the LLM. Verifies installation/repository health using only existing,
already-established read APIs.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from xsight.cli.commands._pipeline import has_repo_changed
from xsight.config.settings import settings
from xsight.database.connection import get_connection
from xsight.database.repositories import get_repository, get_repository_by_id
from xsight.scanner.core import scan
from xsight.vectorstore.core import list_point_ids
from xsight.vectorstore.provider import QdrantVectorStoreProvider

console = Console()


def run(path: Path = typer.Argument(Path("."))) -> None:
    resolved_path = path.expanduser().resolve()

    console.rule("[bold cyan]XSight Doctor[/bold cyan]")
    console.print("[bold cyan]System Diagnostics[/bold cyan]")
    console.print()

    failures = 0
    repo_indexed = False
    repo_stale = False

    # 1. Configuration
    try:
        _ = settings.qdrant_url
        console.print("[green]✓[/green] Configuration loaded")
    except Exception as e:
        console.print("[red]✗[/red] Configuration failed")
        console.print(f"  [dim]{e}[/dim]")
        failures += 1
    console.print()

    # 2. SQLite
    conn = None
    try:
        conn = get_connection()
        console.print("[green]✓[/green] SQLite database reachable")
    except Exception as e:
        console.print("[red]✗[/red] SQLite database unavailable")
        console.print(f"  [dim]{e}[/dim]")
        failures += 1
    console.print()

    # 3. Qdrant
    vector_provider = None
    try:
        vector_provider = QdrantVectorStoreProvider(
            collection_name=settings.qdrant_collection,
            url=settings.qdrant_url,
        )
        vector_provider.collection_exists()
        console.print("[green]✓[/green] Connected to Qdrant")
    except Exception as e:
        console.print("[red]✗[/red] Cannot connect to Qdrant")
        console.print(f"  [dim]{e}[/dim]")
        failures += 1
    console.print()

    # 4. Repository
    repo_id = None
    if conn is not None:
        repo_id = get_repository(resolved_path, conn)
        if repo_id is None:
            console.print("[dim]Repository is not indexed.[/dim]")
        else:
            repo_indexed = True
            console.print("[green]✓[/green] Repository indexed")
    console.print()

    # Repository information panel (only if indexed)
    if conn is not None and repo_id is not None:
        row = get_repository_by_id(repo_id, conn)
        console.print(
            Panel(
                f"[bold]Name[/bold] : {row['name']}\n[bold]Path[/bold] : {row['path']}",
                title="Repository",
                title_align="left",
                border_style="cyan",
            )
        )
        console.print()

    # 5. Repository freshness (only if indexed)
    if conn is not None and repo_id is not None:
        try:
            scan_result = scan(resolved_path)
            index_summary_stale = has_repo_changed(repo_id, scan_result, conn)
            if index_summary_stale:
                console.print("[yellow]![/yellow] Repository changed since last index")
                console.print("  [dim]Run xsight update[/dim]")
                repo_stale = True
            else:
                console.print("[green]✓[/green] Repository index is up-to-date")
        except Exception as e:
            console.print("[red]✗[/red] Could not check repository freshness")
            console.print(f"  [dim]{e}[/dim]")
            failures += 1
        console.print()

    # 6. Vector store (only if indexed)
    if repo_id is not None and vector_provider is not None:
        try:
            point_ids = list_point_ids(repo_id, vector_provider)
            if point_ids:
                console.print(f"[green]✓[/green] Vector store contains {len(point_ids)} embeddings")
            else:
                console.print("[dim]No embeddings found in the vector store.[/dim]")
        except Exception as e:
            console.print("[red]✗[/red] Could not query vector store")
            console.print(f"  [dim]{e}[/dim]")
            failures += 1
        console.print()

    if conn is not None:
        conn.close()

    # Overall status — exactly four states, failures take precedence
    if failures:
        status_text = "Some diagnostic checks failed."
        border_style = "red"
    elif not repo_indexed:
        status_text = "No repository is indexed here.\n\nRun xsight init <path> to begin."
        border_style = "cyan"
    elif repo_stale:
        status_text = "Repository index is out of date.\n\nRun xsight update."
        border_style = "yellow"
    else:
        status_text = "Everything looks healthy."
        border_style = "green"

    console.print(
        Panel(
            status_text,
            title="Overall Status",
            title_align="left",
            border_style=border_style,
        )
    )