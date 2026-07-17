"""`xsight graph` command — raw inspector over the in-memory NetworkX graph.

Read-only, same guard pattern as `architecture`/`modules`/`dependencies`/
`symbols`. No LLM, no embeddings, no visualization, no export formats.
Node inspection uses actual graph node ids only — not symbols.py's
display-friendly names.
"""

from collections import Counter
from pathlib import Path

import typer
from rich.console import Console

from xsight.cli.commands._pipeline import has_repo_changed, load_repo_graph
from xsight.database.connection import get_connection
from xsight.database.repositories import get_repository
from xsight.indexer.models import IndexSummary
from xsight.scanner.core import scan

console = Console()


def _print_stats(graph) -> None:
    node_kinds = Counter(d.get("kind") for _, d in graph.nodes(data=True))
    edge_types = Counter(d.get("type") for _, _, d in graph.edges(data=True))

    console.print("[bold cyan]Nodes[/bold cyan]")
    console.print(f"  Modules:   [bold green]{node_kinds.get('module', 0)}[/bold green]")
    console.print(f"  Classes:   [bold green]{node_kinds.get('class', 0)}[/bold green]")
    console.print(f"  Functions: [bold green]{node_kinds.get('function', 0)}[/bold green]")
    console.print(f"  Total:     [bold green]{graph.number_of_nodes()}[/bold green]")

    console.print()
    console.print("[bold cyan]Edges[/bold cyan]")
    console.print(f"  contains: {edge_types.get('contains', 0)}")
    console.print(f"  inherits: {edge_types.get('inherits', 0)}")
    console.print(f"  imports:  {edge_types.get('imports', 0)}")
    console.print(f"  calls:    {edge_types.get('calls', 0)}")
    console.print(f"  Total:    {graph.number_of_edges()}")


def _print_node(graph, node_id: str) -> None:
    data = graph.nodes[node_id]

    console.print(f"[bold cyan]Node[/bold cyan]  [bold green]{node_id}[/bold green]")
    console.print(f"[bold cyan]Kind[/bold cyan]  {data.get('kind')}")

    attrs = {k: v for k, v in data.items() if k != "kind"}
    if attrs:
        console.print()
        console.print("[bold cyan]Attributes[/bold cyan]")
        for key, value in attrs.items():
            console.print(f"  {key} : {value}")

    outgoing_by_type: dict[str, list[str]] = {}
    for _, target, d in graph.out_edges(node_id, data=True):
        outgoing_by_type.setdefault(d.get("type"), []).append(target)

    if outgoing_by_type:
        console.print()
        console.print("[bold cyan]Outgoing[/bold cyan]")
        for edge_type, targets in outgoing_by_type.items():
            console.print(f"  [green]{edge_type} →[/green]")
            for target in targets:
                console.print(f"      {target}")

    incoming_by_type: dict[str, list[str]] = {}
    for source, _, d in graph.in_edges(node_id, data=True):
        incoming_by_type.setdefault(d.get("type"), []).append(source)

    if incoming_by_type:
        console.print()
        console.print("[bold cyan]Incoming[/bold cyan]")
        for edge_type, sources in incoming_by_type.items():
            console.print(f"  [green]{edge_type} ←[/green]")
            for source in sources:
                console.print(f"      {source}")


def run(
    path: Path = typer.Argument(Path(".")),
    node: str | None = typer.Argument(None, help="Exact graph node id to inspect."),
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

    console.rule(style="green")
    console.print("[bold cyan]XSight[/bold cyan] [dim]v0.1.0[/dim]", justify="center")
    console.print("[white]AI Repository Assistant[/white]", justify="center")
    console.rule(style="green")
    console.print()

    graph = load_repo_graph(resolved_path, repo_id, python_files, unchanged_summary, conn)
    conn.close()

    console.print()
    console.print(f"[bold cyan]Graph[/bold cyan]  [white]{resolved_path}[/white]")
    console.print("[cyan]" + "─" * 55 + "[/cyan]")
    console.print()

    if node is None:
        _print_stats(graph)
        return

    if node not in graph.nodes:
        console.print(f"[red]✗[/red] '{node}' is not a known graph node.")
        console.print()
        console.print("Graph nodes use repository-relative paths, for example:")
        console.print("  [bold green]src/xsight/cli/commands/update.py[/bold green]")
        console.print("  [bold green]src/xsight/parser/core.py::parse[/bold green]")
        console.print()
        console.print("Run [bold]xsight symbols[/bold] or [bold]xsight modules[/bold] to see available nodes.")
        raise typer.Exit(code=1)

    _print_node(graph, node)