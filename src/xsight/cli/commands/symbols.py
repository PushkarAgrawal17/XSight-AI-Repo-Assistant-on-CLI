"""`xsight symbols` command — flat listing of every class/function/method
in the repository. Read-only, same guard pattern as `architecture`/
`modules`/`dependencies`. No LLM, no embeddings, no search/filter.
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


def _module_of(graph, node_id: str) -> str:
    """Resolve the owning module's relative_path via `contains` in-edges.

    Classes: one hop (module -> class).
    Functions: one hop if module-level (module -> function), two hops if a
    method (module -> class -> function). Each hop is asserted single-owner,
    matching the invariant already verified in test_graph_fixture.py.
    """
    owners = [u for u, _, d in graph.in_edges(node_id, data=True) if d.get("type") == "contains"]
    assert len(owners) == 1, f"{node_id} has {len(owners)} contains-owners: {owners}"
    owner = owners[0]

    if graph.nodes[owner].get("kind") == "module":
        return owner

    # owner is a class; resolve one more hop to its module
    class_owners = [
        u for u, _, d in graph.in_edges(owner, data=True) if d.get("type") == "contains"
    ]
    assert len(class_owners) == 1, f"{owner} has {len(class_owners)} contains-owners: {class_owners}"
    return class_owners[0]


def _display_name(graph, node_id: str, data: dict) -> str:
    """class -> ClassName; function -> function_name; method -> ClassName.method_name.
    Uses the parent_id relationship already on the node, not a recomputed id.
    """
    if data["kind"] == "class":
        return data["name"]
    if data.get("is_method") and data.get("parent_id") is not None:
        parent_name = graph.nodes[data["parent_id"]]["name"]
        return f"{parent_name}.{data['name']}"
    return data["name"]


def _kind_label(data: dict) -> str:
    if data["kind"] == "class":
        return "Class"
    return "Method" if data.get("is_method") else "Function"


def run(path: Path = typer.Argument(Path("."))) -> None:
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

    rows = []
    for node_id, data in graph.nodes(data=True):
        if data["kind"] not in ("class", "function"):
            continue
        module = _module_of(graph, node_id)
        rows.append((
            module,
            data["start_line"],
            _display_name(graph, node_id, data),
            _kind_label(data),
            data["end_line"],
        ))

    rows.sort(key=lambda r: (r[0], r[1]))

    console.print()
    console.print(f"[bold cyan]Symbols[/bold cyan]  [white]{resolved_path}[/white]")
    console.print("[cyan]" + "─" * 55 + "[/cyan]")
    console.print()

    table = Table(box=None, show_header=True, header_style="bold cyan", padding=(0, 2), expand=False)
    table.add_column("Symbol", style="bold green", no_wrap=True)
    table.add_column("Kind", style="cyan")
    table.add_column("Module")
    table.add_column("Start", justify="right")
    table.add_column("End", justify="right")

    for module, start_line, symbol, kind, end_line in rows:
        table.add_row(symbol, kind, module, str(start_line), str(end_line))

    console.print(table)
    console.print()
    console.print(f"[green]✓[/green] {len(rows)} symbols")
    console.print()
