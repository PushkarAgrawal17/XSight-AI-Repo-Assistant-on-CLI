"""Fixture test: architecture-style graph statistics (module/class/function
counts, edge counts per type, top-imported-module computation), using the
canonical graph fixture (graph_fixture.FIXTURE_MODULES) already used by
test_graph_fixture.py.

This does not re-test build() structure itself (test_graph_fixture.py owns
that) - it tests the aggregation logic that architecture.py performs on top
of an already-built graph.
"""

from collections import Counter

from xsight.cli.commands._pipeline import build_graph
from xsight.tests.graph_fixture import FIXTURE_MODULES


def main() -> None:
    graph = build_graph(FIXTURE_MODULES)

    module_count = sum(1 for _, d in graph.nodes(data=True) if d["kind"] == "module")
    class_count = sum(1 for _, d in graph.nodes(data=True) if d["kind"] == "class")
    function_count = sum(1 for _, d in graph.nodes(data=True) if d["kind"] == "function")

    assert module_count == 2, f"expected 2 modules, got {module_count}"
    assert class_count == 3, f"expected 3 classes, got {class_count}"
    assert function_count == 3, f"expected 3 functions, got {function_count}"

    edge_counts = Counter(d["type"] for _, _, d in graph.edges(data=True))

    assert edge_counts.get("contains", 0) == 6, f"expected 6 contains edges, got {edge_counts.get('contains', 0)}"
    assert edge_counts.get("inherits", 0) == 1, f"expected 1 inherits edge, got {edge_counts.get('inherits', 0)}"
    assert edge_counts.get("imports", 0) == 0, "fixture has no imports; expected 0 import edges"
    assert edge_counts.get("calls", 0) == 0, "fixture has no calls; expected 0 call edges"

    # top-imported-module aggregation, same logic as architecture.py
    import_in_degree = Counter()
    for _, target, d in graph.edges(data=True):
        if d["type"] == "imports":
            import_in_degree[target] += 1
    top_imported = import_in_degree.most_common(5)

    assert top_imported == [], "fixture has no import edges; top_imported must be empty"

    print("All assertions passed.")
    print(f"  modules={module_count} classes={class_count} functions={function_count}")
    print(f"  contains={edge_counts.get('contains', 0)} "
          f"inherits={edge_counts.get('inherits', 0)} "
          f"imports={edge_counts.get('imports', 0)} "
          f"calls={edge_counts.get('calls', 0)}")


if __name__ == "__main__":
    main()