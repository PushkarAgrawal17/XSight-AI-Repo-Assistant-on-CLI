"""Fixture test: dependency aggregation (default table + single-module mode),
using the canonical graph fixture. Fixture has zero import edges, so this
tests aggregation logic only, not import resolution (covered elsewhere).
"""

from xsight.cli.commands._pipeline import build_graph
from xsight.cli.commands.dependencies import _import_neighbors
from xsight.tests.graph_fixture import FIXTURE_MODULES


def main() -> None:
    graph = build_graph(FIXTURE_MODULES)

    module_ids = sorted(n for n, d in graph.nodes(data=True) if d.get("kind") == "module")
    assert module_ids == ["module_a.py", "module_b.py"], module_ids

    for module_id in module_ids:
        imports, imported_by = _import_neighbors(graph, module_id)
        assert imports == [], f"{module_id}: expected no imports, got {imports}"
        assert imported_by == [], f"{module_id}: expected no imported_by, got {imported_by}"

    # single-module lookup for a known module
    imports, imported_by = _import_neighbors(graph, "module_a.py")
    assert imports == []
    assert imported_by == []

    # unknown module: verified at the graph-membership level (same check run.py performs)
    assert "nonexistent.py" not in graph.nodes

    print("OK: dependency aggregation (empty-import fixture)")
    print(f"  modules checked: {module_ids}")


if __name__ == "__main__":
    main()