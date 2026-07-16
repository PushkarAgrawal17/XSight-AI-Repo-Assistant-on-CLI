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

    console.print("[bold]Nodes[/bold]")
    console.print(f"  Modules:   {node_kinds.get('module', 0)}")
    console.print(f"  Classes:   {node_kinds.get('class', 0)}")
    console.print(f"  Functions: {node_kinds.get('function', 0)}")
    console.print(f"  Total:     {graph.number_of_nodes()}")

    console.print("\n[bold]Edges[/bold]")
    console.print(f"  contains: {edge_types.get('contains', 0)}")
    console.print(f"  inherits: {edge_types.get('inherits', 0)}")
    console.print(f"  imports:  {edge_types.get('imports', 0)}")
    console.print(f"  calls:    {edge_types.get('calls', 0)}")
    console.print(f"  Total:    {graph.number_of_edges()}")


def _print_node(graph, node_id: str) -> None:
    data = graph.nodes[node_id]

    console.print("[bold]Node[/bold]")
    console.print(f"  {node_id}")

    console.print("\n[bold]Kind[/bold]")
    console.print(f"  {data.get('kind')}")

    attrs = {k: v for k, v in data.items() if k != "kind"}
    if attrs:
        console.print("\n[bold]Attributes[/bold]")
        for key, value in attrs.items():
            console.print(f"  {key} : {value}")

    outgoing_by_type: dict[str, list[str]] = {}
    for _, target, d in graph.out_edges(node_id, data=True):
        outgoing_by_type.setdefault(d.get("type"), []).append(target)

    if outgoing_by_type:
        console.print("\n[bold]Outgoing[/bold]")
        for edge_type, targets in outgoing_by_type.items():
            console.print(f"  {edge_type} ->")
            for target in targets:
                console.print(f"      {target}")

    incoming_by_type: dict[str, list[str]] = {}
    for source, _, d in graph.in_edges(node_id, data=True):
        incoming_by_type.setdefault(d.get("type"), []).append(source)

    if incoming_by_type:
        console.print("\n[bold]Incoming[/bold]")
        for edge_type, sources in incoming_by_type.items():
            console.print(f"  {edge_type} <-")
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

    if node is None:
        _print_stats(graph)
        return

    if node not in graph.nodes:
        console.print(
            f"[red]Error:[/red] '{node}' is not a known graph node.\n\n"
            "Graph nodes use repository-relative paths.\n\n"
            "Examples:\n"
            "  • src/xsight/cli/commands/update.py\n"
            "  • src/xsight/parser/core.py::parse\n\n"
            "Run [yellow]xsight symbols[/yellow] or [yellow]xsight modules[/yellow] to see available nodes."
        )
        raise typer.Exit(code=1)

    _print_node(graph, node)