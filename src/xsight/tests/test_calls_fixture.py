"""
Deterministic call resolver regression test.

Runs resolve_calls() against FIXTURE_MODULES (hand-constructed ParsedModule
objects, not run through the real parser) and asserts the exact CallEdge
list it should produce.
"""

from xsight.calls.core import resolve_calls
from xsight.calls.models import CallEdge
from xsight.tests.calls_fixture import FIXTURE_MODULES


def main() -> None:
    edges = resolve_calls(FIXTURE_MODULES)

    # ---- exact expected output, in order ----
    expected = [
        CallEdge(caller_id="main.py::top_level_function", callee_id="main.py::foo"),
        CallEdge(caller_id="main.py::top_level_function", callee_id="helper.py::do_work"),
        CallEdge(caller_id="main.py::top_level_function", callee_id="pkg/mod.py::util"),
        CallEdge(caller_id="main.py::foo", callee_id="main.py::foo"),
        CallEdge(caller_id="main.py::MyClass.method_a", callee_id="main.py::MyClass.method_b"),
    ]
    assert edges == expected, f"expected {expected}, got {edges}"

    # ---- same-module function call ----
    assert CallEdge("main.py::top_level_function", "main.py::foo") in edges

    # ---- same-class self.method() ----
    assert CallEdge("main.py::MyClass.method_a", "main.py::MyClass.method_b") in edges

    # ---- cross-module: from helper import do_work ----
    assert CallEdge("main.py::top_level_function", "helper.py::do_work") in edges

    # ---- cross-module: import pkg.mod ; pkg.mod.util() ----
    assert CallEdge("main.py::top_level_function", "pkg/mod.py::util") in edges

    # ---- unresolved bare call: no edge from top_level_function to anything
    #      named "unresolved_bare" ----
    assert not any(
        e.caller_id == "main.py::top_level_function" and "unresolved_bare" in e.callee_id
        for e in edges
    )

    # ---- unresolved attribute receiver ("obj" is not a resolvable module) ----
    assert not any(
        e.caller_id == "main.py::top_level_function" and e.callee_id.endswith("::method")
        for e in edges
    )

    # ---- ambiguous import skipped (receiver "shared" matches both roots) ----
    assert not any(
        e.caller_id == "main.py::top_level_function"
        and (e.callee_id.startswith("shared.py") or e.callee_id.startswith("src/shared.py"))
        for e in edges
    )

    # ---- duplicate call edges collapse ----
    # top_level_function calls foo() twice -- exactly one edge, not two
    to_foo = [
        e for e in edges
        if e.caller_id == "main.py::top_level_function" and e.callee_id == "main.py::foo"
    ]
    assert len(to_foo) == 1, f"expected duplicate calls to collapse, got {to_foo}"

    # ---- recursive call produces a self-loop edge ----
    assert CallEdge("main.py::foo", "main.py::foo") in edges

    # ---- empty input ----
    assert resolve_calls([]) == []

    print("All assertions passed.")
    print(f"  edges resolved: {len(edges)}")
    for e in edges:
        print(f"    {e.caller_id} -> {e.callee_id}")


if __name__ == "__main__":
    main()
