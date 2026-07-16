"""`xsight modules` command — flat per-module structural listing.

Read-only, same guard pattern as `architecture`: never calls sync(), never
commits, refuses to run against stale cache and instructs `xsight update`
instead. No LLM, no embeddings.
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


def _module_stats(graph, module_id: str) -> tuple[int, int, int, int]:
    """Returns (classes, functions, imports, imported_by) for one module."""
    class_ids = []
    module_level_functions = 0

    for _, target, d in graph.out_edges(module_id, data=True):
        if d.get("type") != "contains":
            continue
        target_kind = graph.nodes[target].get("kind")
        if target_kind == "class":
            class_ids.append(target)
        elif target_kind == "function":
            module_level_functions += 1

    method_count = 0
    for class_id in class_ids:
        for _, target, d in graph.out_edges(class_id, data=True):
            if d.get("type") == "contains" and graph.nodes[target].get("kind") == "function":
                method_count += 1

    imports_out = sum(
        1 for _, _, d in graph.out_edges(module_id, data=True) if d.get("type") == "imports"
    )
    imports_in = sum(
        1 for _, _, d in graph.in_edges(module_id, data=True) if d.get("type") == "imports"
    )

    return len(class_ids), module_level_functions + method_count, imports_out, imports_in


def run(path: Path = typer.Argument(Path("."))) -> None:
    resolved_path = path.expanduser().resolve()
    if not resolved_path.is_dir():
        console.print(f"[red]Error:[/red] '{resolved_path}' is not a directory.")
        raise typer.Exit(code=1)

    conn = get_connection()
    repo_id = get_repository(resolved_path, conn)
    if repo_id is None:
        conn.close()
        console.print("[red]Repository hasn't been indexed. Run `xsight init` first.[/red]")
        raise typer.Exit(code=1)

    scan_result = scan(resolved_path)

    if has_repo_changed(repo_id, scan_result, conn):
        conn.close()
        console.print(
            "[yellow]Repository has changed since the last index.[/yellow]\n"
            "Run [bold]xsight update[/bold] first, then retry."
        )
        raise typer.Exit(code=1)

    python_files = [f for f in scan_result.snapshot.files if f.language == "python"]
    unchanged_summary = IndexSummary(
        added=0, updated=0, removed=0, unchanged=len(python_files),
        total_files=len(python_files),
        added_files=[], updated_files=[], removed_files=[],
    )
    graph = load_repo_graph(resolved_path, repo_id, python_files, unchanged_summary, conn)
    conn.close()

    module_ids = sorted(n for n, d in graph.nodes(data=True) if d.get("kind") == "module")

    table = Table(title=f"Modules — {resolved_path}")
    table.add_column("Module")
    table.add_column("Classes", justify="right")
    table.add_column("Functions", justify="right")
    table.add_column("Imports", justify="right")
    table.add_column("Imported By", justify="right")

    for module_id in module_ids:
        classes, functions, imports_out, imports_in = _module_stats(graph, module_id)
        display_path = graph.nodes[module_id].get("relative_path", module_id)
        table.add_row(display_path, str(classes), str(functions), str(imports_out), str(imports_in))

    console.print(table)