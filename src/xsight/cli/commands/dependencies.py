"""`xsight dependencies` command — import relationships between modules.

Read-only, same guard pattern as `architecture`/`modules`. Default mode
lists every module's import counts; single-module mode shows immediate
imports/imported-by neighbors only (no recursion, no cycle detection).
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from xsight.cli.commands._pipeline import has_repo_changed, load_repo_graph
from xsight.database.connection import get_connection
from xsight.database.repositories import get_repository
from xsight.indexer.models import IndexSummary
from xsight.scanner.core import scan

console = Console()


def _import_neighbors(graph, module_id: str) -> tuple[list[str], list[str]]:
    """Returns (imports, imported_by) as relative_path lists, one-hop only."""
    imports = [
        graph.nodes[target].get("relative_path", target)
        for _, target, d in graph.out_edges(module_id, data=True)
        if d.get("type") == "imports"
    ]
    imported_by = [
        graph.nodes[source].get("relative_path", source)
        for source, _, d in graph.in_edges(module_id, data=True)
        if d.get("type") == "imports"
    ]
    return sorted(imports), sorted(imported_by)


def run(
    path: Path = typer.Argument(Path(".")),
    module: str | None = typer.Argument(None, help="Optional module relative_path to inspect."),
) -> None:
    resolved_path = path.expanduser().resolve()
    if not resolved_path.is_dir():
        console.print(f"[red]Error:[/red] '{resolved_path}' is not a directory.")
        raise typer.Exit(code=1)

    conn = get_connection()
    repo_id = get_repository(resolved_path, conn)
    if repo_id is None:
        conn.close()
        console.print("[red]Repository hasn't been indexed. Run [bold]`xsight init`[/bold] first.[/red]")
        raise typer.Exit(code=1)

    scan_result = scan(resolved_path)

    if has_repo_changed(repo_id, scan_result, conn):
        conn.close()
        console.print("[yellow]⚠ Repository has changed since the last index. [/yellow] ")
        console.print("[yellow]Run [bold]xsight update[/bold] first, then retry.[/yellow]")
        raise typer.Exit(code=1)

    python_files = [f for f in scan_result.snapshot.files if f.language == "python"]
    unchanged_summary = IndexSummary(
        added=0, updated=0, removed=0, unchanged=len(python_files),
        total_files=len(python_files),
        added_files=[], updated_files=[], removed_files=[],
    )
    graph = load_repo_graph(resolved_path, repo_id, python_files, unchanged_summary, conn)
    conn.close()

    if module is None:
        module_ids = sorted(n for n, d in graph.nodes(data=True) if d.get("kind") == "module")

        console.print()
        console.print(f"[bold cyan]Dependencies [/bold cyan]  [white bold]{resolved_path}[/white bold]")
        console.print("[cyan]" + "─" * 60 + "[/cyan]")
        console.print()

        table = Table(box=None, show_header=True, header_style="bold cyan", padding=(0, 2), expand=False)
        table.add_column("Module", style="bold green", no_wrap=True)
        table.add_column("Imports", justify="right")
        table.add_column("Imported By", justify="right")

        for module_id in module_ids:
            imports, imported_by = _import_neighbors(graph, module_id)
            display_path = graph.nodes[module_id].get("relative_path", module_id)
            table.add_row(display_path, str(len(imports)), str(len(imported_by)))

        console.print(table)
        console.print()
        console.print(f"[green]✓[/green] {len(module_ids)} modules")
        console.print()
        return

    if module not in graph.nodes or graph.nodes[module].get("kind") != "module":
        console.print(f"[red]✗[/red] '{module}' is not a known module in this repository.")
        raise typer.Exit(code=1)

    imports, imported_by = _import_neighbors(graph, module)

    console.print(f"[bold cyan]Module[/bold cyan]  [bold green]{module}[/bold green]")
    console.print()

    console.print("[bold cyan]Imports[/bold cyan]")
    console.print("[cyan]" + "─" * 30 + "[/cyan]")
    if imports:
        for m in imports:
            console.print(f"  [green]→[/green] {m}")
    else:
        console.print("  [yellow]○[/yellow] none")

    console.print()
    console.print("[bold cyan]Imported By[/bold cyan]")
    console.print("[cyan]" + "─" * 30 + "[/cyan]")
    if imported_by:
        for m in imported_by:
            console.print(f"  [green]←[/green] {m}")
    else:
        console.print("  [yellow]○[/yellow] none")
