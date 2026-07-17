from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from xsight.cli.commands._pipeline import has_repo_changed
from xsight.config.settings import settings
from xsight.database.connection import get_connection
from xsight.database.repositories import get_repository, get_repository_by_id
from xsight.scanner.core import scan
from xsight.vectorstore.core import list_point_ids
from xsight.vectorstore.provider import QdrantVectorStoreProvider

console = Console()


def _status(ok: bool) -> str:
    return "[green]✓[/green]" if ok else "[red]✗[/red]"


def run(path: Path = typer.Argument(Path("."))) -> None:
    resolved_path = path.expanduser().resolve()

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

    failures = 0
    repo_indexed = False
    repo_stale = False

    diagnostics = Table(
        title="[bold cyan]System Diagnostics[/bold cyan]",
        box=None,
        show_header=False,
        padding=(0, 2),
        expand=False,
    )

    diagnostics.add_column(no_wrap=True)
    diagnostics.add_column(style="bold")
    diagnostics.add_column()

    # ------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------

    try:
        _ = settings.qdrant_url
        diagnostics.add_row(
            _status(True),
            "Configuration",
            "Loaded successfully",
        )
    except Exception as e:
        diagnostics.add_row(
            _status(False),
            "Configuration",
            str(e),
        )
        failures += 1

    # ------------------------------------------------------------
    # SQLite
    # ------------------------------------------------------------

    conn = None

    try:
        conn = get_connection()
        diagnostics.add_row(
            _status(True),
            "SQLite",
            "Database reachable",
        )
    except Exception as e:
        diagnostics.add_row(
            _status(False),
            "SQLite",
            str(e),
        )
        failures += 1

    # ------------------------------------------------------------
    # Qdrant
    # ------------------------------------------------------------

    vector_provider = None

    try:
        vector_provider = QdrantVectorStoreProvider(
            collection_name=settings.qdrant_collection,
            url=settings.qdrant_url,
        )

        vector_provider.collection_exists()

        diagnostics.add_row(
            _status(True),
            "Qdrant",
            "Connected",
        )

    except Exception as e:
        diagnostics.add_row(
            _status(False),
            "Qdrant",
            str(e),
        )
        failures += 1

    # ------------------------------------------------------------
    # Repository
    # ------------------------------------------------------------

    repo_id = None

    if conn is not None:
        repo_id = get_repository(resolved_path, conn)

        if repo_id is None:
            diagnostics.add_row(
                "[yellow]○[/yellow]",
                "Repository",
                "Not indexed",
            )
        else:
            repo_indexed = True
            diagnostics.add_row(
                _status(True),
                "Repository",
                "Indexed",
            )

    # ------------------------------------------------------------
    # Freshness
    # ------------------------------------------------------------

    if conn is not None and repo_id is not None:
        try:
            scan_result = scan(resolved_path)

            if has_repo_changed(repo_id, scan_result, conn):
                repo_stale = True
                diagnostics.add_row(
                    "[yellow]⚠[/yellow]",
                    "Repository",
                    "Index is out of date",
                )
            else:
                diagnostics.add_row(
                    _status(True),
                    "Repository",
                    "Index is up to date",
                )

        except Exception as e:
            diagnostics.add_row(
                _status(False),
                "Repository",
                str(e),
            )
            failures += 1

    # ------------------------------------------------------------
    # Vector Store
    # ------------------------------------------------------------

    if repo_id is not None and vector_provider is not None:
        try:
            embeddings = len(list_point_ids(repo_id, vector_provider))

            diagnostics.add_row(
                _status(True) if embeddings else "[yellow]○[/yellow]",
                "Embeddings",
                f"{embeddings} stored",
            )

        except Exception as e:
            diagnostics.add_row(
                _status(False),
                "Embeddings",
                str(e),
            )
            failures += 1

    console.print(diagnostics)
    console.print()

    # ------------------------------------------------------------
    # Repository Information
    # ------------------------------------------------------------

    if conn is not None and repo_id is not None:
        row = get_repository_by_id(repo_id, conn)

        console.print(
            Panel(
                f"[bold]Name[/bold] : {row['name']}\n"
                f"[bold]Path[/bold] : {row['path']}",
                title="📦 Repository",
                border_style="cyan",
                title_align="left",
            )
        )

        console.print()

    if conn is not None:
        conn.close()

    # ------------------------------------------------------------
    # Overall Status
    # ------------------------------------------------------------

    if failures:
        title = "✗ Overall Status"
        border = "red"
        message = (
            "[red]Some diagnostic checks failed.[/red]\n\n"
            "Resolve the reported issues and run [bold]xsight doctor[/bold] again."
        )

    elif not repo_indexed:
        title = "○ Overall Status"
        border = "cyan"
        message = (
            "No repository is indexed here.\n\n"
            "Run [bold]xsight init <path>[/bold] to begin."
        )

    elif repo_stale:
        title = "⚠ Overall Status"
        border = "yellow"
        message = (
            "Repository index is out of date.\n\n"
            "Run [bold]xsight update[/bold]."
        )

    else:
        title = "✓ Overall Status"
        border = "green"
        message = (
            "[green]Everything looks healthy.[/green]\n\n"
            "XSight is ready."
        )

    console.print(
        Panel(
            message,
            title=title,
            border_style=border,
            title_align="left",
        )
    )