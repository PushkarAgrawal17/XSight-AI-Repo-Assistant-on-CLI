"""`xsight update` command — re-indexes an already-initialized repository."""

from pathlib import Path
import sqlite3

import typer
from rich.console import Console

from xsight.cli.commands._pipeline import run_pipeline
from xsight.database.repositories import get_repository

console = Console()


def run(
    path: Path = typer.Argument(
        Path("."),
        help="Path to the repository to update. Defaults to the current directory.",
    ),
) -> None:
    """Re-index an already-initialized repository incrementally."""
    resolved_path = path.expanduser().resolve()
    if not resolved_path.is_dir():
        console.print(f"[red]Error:[/red] '{resolved_path}' is not a directory.")
        raise typer.Exit(code=1)

    def require_existing(p: Path, conn: sqlite3.Connection) -> int:
        repo_id = get_repository(p, conn)
        if repo_id is None:
            console.print(
                f"[red]Error:[/red] '{p}' has not been indexed yet.\n"
                "  Run [bold]xsight init[/bold] first."
            )
            raise typer.Exit(code=1)
        return repo_id

    run_pipeline(resolved_path, require_existing)