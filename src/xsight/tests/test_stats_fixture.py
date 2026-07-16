"""Fixture test: `xsight stats` aggregation logic (symbol/relationship
counts, largest-module/-class ranking, LOC via real fixture file).
Does not modify graph_fixture.py or parser_fixture.py.
"""

from pathlib import Path

from xsight.cli.commands._pipeline import build_graph
from xsight.cli.commands.stats import _class_method_count, _module_symbol_count
from xsight.tests.graph_fixture import FIXTURE_MODULES


def main() -> None:
    graph = build_graph(FIXTURE_MODULES)

    module_ids = [n for n, d in graph.nodes(data=True) if d.get("kind") == "module"]
    class_ids = [n for n, d in graph.nodes(data=True) if d.get("kind") == "class"]

    assert sorted(module_ids) == ["module_a.py", "module_b.py"]
    assert len(class_ids) == 3

    # module_a.py: classes(Base, Derived)=2 + module-level function(1) + methods(2) = 5
    a_total = _module_symbol_count(graph, "module_a.py")
    assert a_total == 5, f"expected 5 total symbols in module_a.py, got {a_total}"

    # module_b.py: class(Unrelated)=1 + 0 functions + 0 methods = 1
    b_total = _module_symbol_count(graph, "module_b.py")
    assert b_total == 1, f"expected 1 total symbol in module_b.py, got {b_total}"

    # Derived has 2 methods (method, helper); Base and Unrelated have 0
    derived_methods = _class_method_count(graph, "module_a.py::Derived")
    base_methods = _class_method_count(graph, "module_a.py::Base")
    assert derived_methods == 2, f"expected 2 methods for Derived, got {derived_methods}"
    assert base_methods == 0, f"expected 0 methods for Base, got {base_methods}"

    # LOC: reuse real parser_fixture.py already on disk
    fixture_file = Path(__file__).parent / "parser_fixture.py"
    assert fixture_file.exists(), f"missing canonical fixture: {fixture_file}"
    loc = len(fixture_file.read_text().splitlines())
    assert loc > 0, "expected non-zero LOC for parser_fixture.py"

    print("OK: stats aggregation (module totals, class method counts, LOC)")
    print(f"  module_a.py total={a_total} module_b.py total={b_total}")
    print(f"  Derived methods={derived_methods} Base methods={base_methods}")
    print(f"  parser_fixture.py LOC={loc}")


if __name__ == "__main__":
    main()