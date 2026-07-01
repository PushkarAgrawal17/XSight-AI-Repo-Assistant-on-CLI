"""`xsight init` command."""

from pathlib import Path

import typer


def run(
    path: Path = typer.Argument(
        Path("."),
        help="Path to the repository to index. Defaults to the current directory.",
    ),
) -> None:
    """Index a repository: scan files, detect languages, store metadata."""
    raise NotImplementedError("Scanner not implemented yet.")
