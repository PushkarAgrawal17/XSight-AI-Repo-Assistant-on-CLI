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
        console.print("[red]Repository hasn't been indexed. Run [bold]`xsight init`[/bold] first.[/red]")
        raise typer.Exit(code=1)

    scan_result = scan(resolved_path)  # filesystem read only, no DB write

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

    console.print()
    console.print(f"[bold cyan]Architecture[/bold cyan]  [white bold]{resolved_path}[/white bold]")
    console.print("[cyan]" + "─" * 60 + "[/cyan]")
    console.print()

    console.print("[bold cyan]Files[/bold cyan]")
    breakdown = ", ".join(f"{c} {lang}" for lang, c in language_counts.most_common())
    console.print(f"  Total: {len(scan_result.snapshot.files)}" + (f" ({breakdown})" if breakdown else ""))

    console.print()
    console.print("[bold cyan]Structure[/bold cyan]")
    console.print(f"  Modules:   [bold green]{module_count}[/bold green]")
    console.print(f"  Classes:   [bold green]{class_count}[/bold green]")
    console.print(f"  Functions: [bold green]{function_count}[/bold green]")

    console.print()
    console.print("[bold cyan]Relationships[/bold cyan]")
    console.print(f"  contains:  {edge_counts.get('contains', 0)} edges")
    console.print(f"  inherits:  {edge_counts.get('inherits', 0)} edges [dim](same-module only)[/dim]")
    console.print(f"  imports:   {edge_counts.get('imports', 0)} edges")
    console.print(f"  calls:     {edge_counts.get('calls', 0)} edges [dim](statically resolvable only)[/dim]")

    if top_imported:
        console.print()
        console.print("[bold cyan]Most Imported Modules[/bold cyan]")
        for i, (node_id, count) in enumerate(top_imported, start=1):
            display_path = graph.nodes[node_id].get("relative_path", node_id)
            console.print(f"  {i}. [bold green]{display_path}[/bold green] — {count} importers")
