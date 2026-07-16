"""`xsight architecture` command — structural repository overview.

Read-only: never calls sync() or commits. Uses whatever is already indexed.
No LLM, no embeddings, no retrieval.
"""

from pathlib import Path
from collections import Counter

import typer
from rich.console import Console

from xsight.cli.commands._pipeline import load_repo_graph, has_repo_changed
from xsight.database.connection import get_connection
from xsight.database.repositories import get_repository
from xsight.indexer.models import IndexSummary
from xsight.scanner.core import scan

console = Console()


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

    scan_result = scan(resolved_path)  # filesystem read only, no DB write

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

    language_counts = Counter(f.language for f in scan_result.snapshot.files if f.language)
    module_count = sum(1 for _, d in graph.nodes(data=True) if d.get("kind") == "module")
    class_count = sum(1 for _, d in graph.nodes(data=True) if d.get("kind") == "class")
    function_count = sum(1 for _, d in graph.nodes(data=True) if d.get("kind") == "function")
    edge_counts = Counter(d.get("type") for _, _, d in graph.edges(data=True))

    import_in_degree = Counter()
    for _, target, d in graph.edges(data=True):
        if d.get("type") == "imports":
            import_in_degree[target] += 1
    top_imported = import_in_degree.most_common(5)

    console.print(f"[bold]Repository:[/bold] {resolved_path}\n")
    console.print("[bold]Files[/bold]")
    breakdown = ", ".join(f"{c} {lang}" for lang, c in language_counts.most_common())
    console.print(f"  Total: {len(scan_result.snapshot.files)}" + (f" ({breakdown})" if breakdown else ""))
    console.print("\n[bold]Structure[/bold]")
    console.print(f"  Modules:   {module_count}")
    console.print(f"  Classes:   {class_count}")
    console.print(f"  Functions: {function_count}")
    console.print("\n[bold]Relationships[/bold]")
    console.print(f"  contains:  {edge_counts.get('contains', 0)} edges")
    console.print(f"  inherits:  {edge_counts.get('inherits', 0)} edges (same-module only)")
    console.print(f"  imports:   {edge_counts.get('imports', 0)} edges")
    console.print(f"  calls:     {edge_counts.get('calls', 0)} edges (statically resolvable only)")

    if top_imported:
        console.print("\n[bold]Most imported modules[/bold]")
        for i, (node_id, count) in enumerate(top_imported, start=1):
            # Point 4 fix: display the node's relative_path attribute, not
            # the raw node id, so this matches what users see elsewhere.
            display_path = graph.nodes[node_id].get("relative_path", node_id)
            console.print(f"  {i}. {display_path} ({count} importers)")