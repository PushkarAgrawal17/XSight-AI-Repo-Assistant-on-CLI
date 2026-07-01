"""`xsight init` command."""

from pathlib import Path

import typer
from rich.console import Console

from xsight.database.connection import get_connection
from xsight.database.repositories import get_or_create_repository
from xsight.indexer.core import sync
from xsight.scanner.core import scan

console = Console()


def run(
    path: Path = typer.Argument(
        Path("."),
        help="Path to the repository to index. Defaults to the current directory.",
    ),
) -> None:
    """Index a repository: scan files, detect languages, store metadata."""
    resolved_path = path.expanduser().resolve()

    if not resolved_path.is_dir():
        console.print(f"[red]Error:[/red] '{resolved_path}' is not a directory.")
        raise typer.Exit(code=1)

    conn = get_connection()
    try:
        result = scan(resolved_path)
        repo_id = get_or_create_repository(result.snapshot.repo_path, conn)
        summary = sync(repo_id, result.snapshot, conn)
    finally:
        conn.close()

    _render_summary(resolved_path, result.summary, summary)


def _render_summary(repo_path: Path, scan_summary, index_summary) -> None:
    console.print(f"[bold green]Indexed[/bold green] {repo_path}")
    console.print(
        f"  files: {index_summary.total_files} total "
        f"([green]+{index_summary.added}[/green] "
        f"[yellow]~{index_summary.updated}[/yellow] "
        f"[red]-{index_summary.removed}[/red] "
        f"={index_summary.unchanged})"
    )
    console.print(
        f"  skipped: {scan_summary.ignored_files} ignored files, "
        f"{scan_summary.ignored_directories} ignored dirs, "
        f"{scan_summary.skipped_binary_files} binary, "
        f"{scan_summary.skipped_large_files} too large"
    )
    if scan_summary.errors:
        console.print(f"  [red]{scan_summary.errors} files skipped due to errors[/red]")