"""Fixture test: per-module structural stats (classes, functions including
methods, imports, imported-by), using the canonical graph fixture.
"""

from xsight.cli.commands._pipeline import build_graph
from xsight.cli.commands.modules import _module_stats
from xsight.tests.graph_fixture import FIXTURE_MODULES


def main() -> None:
    graph = build_graph(FIXTURE_MODULES)

    module_ids = sorted(n for n, d in graph.nodes(data=True) if d.get("kind") == "module")
    assert module_ids == ["module_a.py", "module_b.py"], module_ids

    a_classes, a_functions, a_imports, a_imported_by = _module_stats(graph, "module_a.py")
    assert a_classes == 2, f"expected 2 classes, got {a_classes}"
    assert a_functions == 3, f"expected 3 functions (1 top-level + 2 methods), got {a_functions}"
    assert a_imports == 0
    assert a_imported_by == 0

    b_classes, b_functions, b_imports, b_imported_by = _module_stats(graph, "module_b.py")
    assert b_classes == 1, f"expected 1 class, got {b_classes}"
    assert b_functions == 0, f"expected 0 functions, got {b_functions}"
    assert b_imports == 0
    assert b_imported_by == 0

    print("OK: per-module stats (classes/functions incl. methods/imports)")
    print(f"  module_a.py: classes={a_classes} functions={a_functions}")
    print(f"  module_b.py: classes={b_classes} functions={b_functions}")


if __name__ == "__main__":
    main()