"""Fixture test: `xsight graph` statistics + one-hop node inspection,
using the canonical graph fixture. Does not modify graph_fixture.py.
"""

from collections import Counter

from xsight.cli.commands._pipeline import build_graph
from xsight.tests.graph_fixture import FIXTURE_MODULES


def main() -> None:
    graph = build_graph(FIXTURE_MODULES)

    node_kinds = Counter(d.get("kind") for _, d in graph.nodes(data=True))
    edge_types = Counter(d.get("type") for _, _, d in graph.edges(data=True))

    assert node_kinds.get("module", 0) == 2, node_kinds
    assert node_kinds.get("class", 0) == 3, node_kinds
    assert node_kinds.get("function", 0) == 3, node_kinds
    assert graph.number_of_nodes() == 8, graph.number_of_nodes()

    assert edge_types.get("contains", 0) == 6, edge_types
    assert edge_types.get("inherits", 0) == 1, edge_types
    assert edge_types.get("imports", 0) == 0, edge_types
    assert edge_types.get("calls", 0) == 0, edge_types
    assert graph.number_of_edges() == 7, graph.number_of_edges()

    # Node inspection: module_a.py
    outgoing = [target for _, target, d in graph.out_edges("module_a.py", data=True)
                if d.get("type") == "contains"]
    assert sorted(outgoing) == sorted([
        "module_a.py::Base", "module_a.py::Derived", "module_a.py::top_level_function",
    ]), outgoing

    incoming = list(graph.in_edges("module_a.py", data=True))
    assert incoming == [], f"expected no incoming edges, got {incoming}"

    print("OK: graph stats + module_a.py one-hop inspection")
    print(f"  nodes={graph.number_of_nodes()} edges={graph.number_of_edges()}")


if __name__ == "__main__":
    main()