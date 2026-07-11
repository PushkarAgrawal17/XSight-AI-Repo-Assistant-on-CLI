"""`xsight init` command."""

from pathlib import Path

import typer
from rich.console import Console

from xsight.cli.commands._pipeline import run_pipeline
from xsight.database.repositories import get_or_create_repository

console = Console()


def run(
    path: Path = typer.Argument(
        Path("."),
        help="Path to the repository to index. Defaults to the current directory.",
    ),
) -> None:
    """Index a repository: scan, parse, build a knowledge graph, and embed it."""
    resolved_path = path.expanduser().resolve()
    if not resolved_path.is_dir():
        console.print(f"[red]Error:[/red] '{resolved_path}' is not a directory.")
        raise typer.Exit(code=1)

    run_pipeline(resolved_path, get_or_create_repository)