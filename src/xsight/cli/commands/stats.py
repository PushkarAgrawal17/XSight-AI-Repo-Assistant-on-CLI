"""`xsight stats` command — numeric repository dashboard (cloc/git-diff-stat
style). Read-only, same guard pattern as architecture/modules/dependencies/
symbols/graph. No LLM, no embeddings, no retrieval.
"""

from pathlib import Path

import typer
from rich.console import Console

from xsight.cli.commands._pipeline import has_repo_changed, load_repo_graph
from xsight.database.connection import get_connection
from xsight.database.repositories import get_repository
from xsight.indexer.models import IndexSummary
from xsight.scanner.core import scan

console = Console()

TOP_N = 5


def _module_symbol_count(graph, module_id: str) -> int:
    total = 0
    class_ids = []
    for _, target, d in graph.out_edges(module_id, data=True):
        if d.get("type") != "contains":
            continue
        kind = graph.nodes[target].get("kind")
        if kind == "class":
            class_ids.append(target)
            total += 1
        elif kind == "function":
            total += 1
    for class_id in class_ids:
        for _, target, d in graph.out_edges(class_id, data=True):
            if d.get("type") == "contains" and graph.nodes[target].get("kind") == "function":
                total += 1
    return total


def _class_method_count(graph, class_id: str) -> int:
    return sum(
        1 for _, target, d in graph.out_edges(class_id, data=True)
        if d.get("type") == "contains" and graph.nodes[target].get("kind") == "function"
    )


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

    console.rule(style="green")
    console.print("[bold cyan]XSight[/bold cyan] [dim]v0.1.0[/dim]", justify="center")
    console.print("[white]AI Repository Assistant[/white]", justify="center")
    console.rule(style="green")
    console.print()

    all_files = scan_result.snapshot.files
    python_files = [f for f in all_files if f.language == "python"]
    unchanged_summary = IndexSummary(
        added=0, updated=0, removed=0, unchanged=len(python_files),
        total_files=len(python_files),
        added_files=[], updated_files=[], removed_files=[],
    )
    graph = load_repo_graph(resolved_path, repo_id, python_files, unchanged_summary, conn)
    conn.close()

    # ---- Files ----
    total_files = len(all_files)
    md_files = sum(1 for f in all_files if f.language == "markdown")
    other_files = total_files - len(python_files) - md_files

    # ---- Symbols / Relationships ----
    module_ids = [n for n, d in graph.nodes(data=True) if d.get("kind") == "module"]
    class_ids = [n for n, d in graph.nodes(data=True) if d.get("kind") == "class"]
    function_nodes = [(n, d) for n, d in graph.nodes(data=True) if d.get("kind") == "function"]
    method_count = sum(1 for _, d in function_nodes if d.get("is_method"))
    function_count = len(function_nodes) - method_count

    edge_counts = {"contains": 0, "inherits": 0, "imports": 0, "calls": 0}
    for _, _, d in graph.edges(data=True):
        t = d.get("type")
        if t in edge_counts:
            edge_counts[t] += 1

    # ---- Code / LOC (reread files) ----
    total_loc = 0
    for f in all_files:
        file_path = resolved_path / f.relative_path
        try:
            total_loc += len(file_path.read_text(errors="replace").splitlines())
        except OSError:
            continue
    avg_loc_per_file = total_loc / total_files if total_files else 0
    avg_functions_per_module = (function_count + method_count) / len(module_ids) if module_ids else 0
    avg_methods_per_class = method_count / len(class_ids) if class_ids else 0

    # ---- Largest Modules (by total symbols) ----
    module_totals = sorted(
        ((graph.nodes[m].get("relative_path", m), _module_symbol_count(graph, m)) for m in module_ids),
        key=lambda x: x[1], reverse=True,
    )[:TOP_N]

    # ---- Largest Classes (by method count) ----
    class_totals = sorted(
        ((graph.nodes[c]["name"], _class_method_count(graph, c)) for c in class_ids),
        key=lambda x: x[1], reverse=True,
    )[:TOP_N]

    # ---- Render ----
    console.print()
    console.print(f"[bold cyan]Statistics[/bold cyan]  [white]{resolved_path}[/white]")
    console.print("[cyan]" + "─" * 55 + "[/cyan]")
    console.print()

    console.print("[bold cyan]Files[/bold cyan]")
    console.print(f"  Total files:    {total_files}")
    console.print(f"  Python files:   {len(python_files)}")
    console.print(f"  Markdown files: {md_files}")
    console.print(f"  Other files:    {other_files}")

    console.print()
    console.print("[bold cyan]Symbols[/bold cyan]")
    console.print(f"  Modules:   [bold green]{len(module_ids)}[/bold green]")
    console.print(f"  Classes:   [bold green]{len(class_ids)}[/bold green]")
    console.print(f"  Functions: [bold green]{function_count}[/bold green]")
    console.print(f"  Methods:   [bold green]{method_count}[/bold green]")

    console.print()
    console.print("[bold cyan]Relationships[/bold cyan]")
    console.print(f"  contains: {edge_counts['contains']}")
    console.print(f"  inherits: {edge_counts['inherits']}")
    console.print(f"  imports:  {edge_counts['imports']}")
    console.print(f"  calls:    {edge_counts['calls']}")

    console.print()
    console.print("[bold cyan]Code[/bold cyan]")
    console.print(f"  Total LOC:                 {total_loc}")
    console.print(f"  Average LOC / file:        {avg_loc_per_file:.1f}")
    console.print(f"  Average functions / module: {avg_functions_per_module:.1f}")
    console.print(f"  Average methods / class:    {avg_methods_per_class:.1f}")

    console.print()
    console.print("[bold cyan]Largest Modules[/bold cyan] [dim](by total symbols)[/dim]")
    for name, count in module_totals:
        console.print(f"  [bold green]{name:<40}[/bold green] {count} symbols")

    console.print()
    console.print("[bold cyan]Largest Classes[/bold cyan] [dim](by method count)[/dim]")
    for name, count in class_totals:
        console.print(f"  [bold green]{name:<40}[/bold green] {count} methods")
