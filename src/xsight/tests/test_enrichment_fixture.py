"""
Deterministic graph enrichment regression test.

Builds a graph from the existing graph fixture, then verifies
add_import_edges() writes exactly one 'imports' edge per ImportEdge given,
performing no resolution or deduplication of its own.
"""

from xsight.graph.builder import build
from xsight.graph.enrichment import add_import_edges
from xsight.imports.models import ImportEdge
from xsight.tests.graph_fixture import FIXTURE_MODULES


def has_edge_of_type(graph, u: str, v: str, edge_type: str) -> bool:
    if not graph.has_edge(u, v):
        return False
    return any(data["type"] == edge_type for data in graph[u][v].values())


def main() -> None:
    graph = build(FIXTURE_MODULES)
    edges_before = graph.number_of_edges()

    import_edges = [
        ImportEdge(source_module="module_a.py", target_module="module_b.py"),
        ImportEdge(source_module="module_b.py", target_module="module_a.py"),
    ]
    add_import_edges(graph, import_edges)

    # ---- exactly one edge per ImportEdge given ----
    assert graph.number_of_edges() == edges_before + len(import_edges), (
        f"expected {len(import_edges)} new edges, "
        f"got {graph.number_of_edges() - edges_before}"
    )

    # ---- correct type and direction for each ----
    assert has_edge_of_type(graph, "module_a.py", "module_b.py", "imports")
    assert has_edge_of_type(graph, "module_b.py", "module_a.py", "imports")

    # ---- enrichment must not touch pre-existing edge types ----
    assert has_edge_of_type(graph, "module_a.py::Derived", "module_a.py::Base", "inherits"), (
        "add_import_edges() must not disturb existing inherits edges"
    )

    # ---- empty edge list changes nothing ----
    edges_after_first = graph.number_of_edges()
    add_import_edges(graph, [])
    assert graph.number_of_edges() == edges_after_first

    print("All assertions passed.")
    print(f"  edges before enrichment: {edges_before}")
    print(f"  edges after enrichment:  {graph.number_of_edges()}")


if __name__ == "__main__":
    main()