"""Fixture test: symbol listing (qualified display names, kind labels,
module resolution, ordering), using the canonical graph fixture.
Does not modify graph_fixture.py.
"""

from xsight.cli.commands._pipeline import build_graph
from xsight.cli.commands.symbols import _display_name, _kind_label, _module_of
from xsight.tests.graph_fixture import FIXTURE_MODULES


def main() -> None:
    graph = build_graph(FIXTURE_MODULES)

    rows = []
    for node_id, data in graph.nodes(data=True):
        if data["kind"] not in ("class", "function"):
            continue
        module = _module_of(graph, node_id)
        rows.append((module, data["start_line"], _display_name(graph, node_id, data), _kind_label(data)))

    rows.sort(key=lambda r: (r[0], r[1]))

    class_count = sum(1 for r in rows if r[3] == "Class")
    function_count = sum(1 for r in rows if r[3] == "Function")
    method_count = sum(1 for r in rows if r[3] == "Method")

    assert class_count == 3, f"expected 3 classes, got {class_count}"
    assert function_count == 1, f"expected 1 function, got {function_count}"
    assert method_count == 2, f"expected 2 methods, got {method_count}"
    assert len(rows) == 6, f"expected 6 rows, got {len(rows)}"

    expected = [
        ("module_a.py", 1, "Base", "Class"),
        ("module_a.py", 2, "Derived", "Class"),
        ("module_a.py", 3, "Derived.method", "Method"),
        ("module_a.py", 4, "top_level_function", "Function"),
        ("module_a.py", 10, "Derived.helper", "Method"),
        ("module_b.py", 1, "Unrelated", "Class"),
    ]
    assert rows == expected, f"row ordering/content mismatch:\n{rows}\nvs\n{expected}"

    print("OK: symbol listing (qualified names, kinds, ordering)")
    print(f"  classes={class_count} functions={function_count} methods={method_count} rows={len(rows)}")


if __name__ == "__main__":
    main()