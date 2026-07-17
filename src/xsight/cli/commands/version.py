"""`xsight version` command — purely informational, standard library only.

No database, no Qdrant, no repository scanning, no graph construction, no
embeddings, no external service contact. Version is read exclusively from
installed package metadata (pyproject.toml is the single source of truth
via importlib.metadata) — no separate __version__ variable is maintained.
"""

import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def _xsight_version() -> str:
    try:
        return version("xsight")
    except PackageNotFoundError:
        return "development"


def _install_path() -> str:
    try:
        from importlib.util import find_spec
        spec = find_spec("xsight")
        if spec is None or spec.origin is None:
            return "unknown"
        return str(Path(spec.origin).resolve().parent)
    except Exception:
        return "unknown"


def run() -> None:
    console.rule(style="green")
    console.print("[bold cyan]XSight[/bold cyan] [dim]v0.1.0[/dim]", justify="center")
    console.print("[white]AI Repository Assistant[/white]", justify="center")
    console.rule(style="green")
    console.print()

    console.print(
        Panel(
            f"[bold]Version[/bold]      : {_xsight_version()}\n"
            f"[bold]Python[/bold]       : {platform.python_version()}\n"
            f"[bold]Platform[/bold]     : {platform.platform()}\n"
            f"[bold]Install Path[/bold] : {_install_path()}",
            title="[bold cyan]System Info[/bold cyan]",
            title_align="left",
            border_style="cyan",
        )
    )
    console.print()
