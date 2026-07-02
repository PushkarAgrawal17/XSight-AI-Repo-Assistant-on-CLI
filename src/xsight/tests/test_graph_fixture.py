"""
Deterministic graph builder regression test.

Builds a graph from FIXTURE_MODULES (hand-constructed ParsedModule objects,
not run through the real parser) and asserts the exact node/edge structure
build() should produce.
"""

from xsight.graph.builder import build
from xsight.tests.graph_fixture import FIXTURE_MODULES


def main() -> None:
    graph = build(FIXTURE_MODULES)

    # ---- node counts ----
    modules = [n for n, d in graph.nodes(data=True) if d["kind"] == "module"]
    classes = [n for n, d in graph.nodes(data=True) if d["kind"] == "class"]
    functions = [n for n, d in graph.nodes(data=True) if d["kind"] == "function"]

    assert len(modules) == 2, f"expected 2 module nodes, got {len(modules)}"
    assert len(classes) == 3, f"expected 3 class nodes, got {len(classes)}"
    assert len(functions) == 2, f"expected 2 function nodes, got {len(functions)}"

    # ---- module node attributes ----
    assert graph.nodes["module_a.py"]["name"] == "module_a"
    assert graph.nodes["module_a.py"]["relative_path"] == "module_a.py"

    # ---- class node attributes ----
    derived = graph.nodes["module_a.py::Derived"]
    assert derived["kind"] == "class"
    assert derived["name"] == "Derived"
    assert derived["base_classes"] == ["Base"]
    assert derived["start_line"] == 2 and derived["end_line"] == 3

    # ---- function node attributes ----
    method = graph.nodes["module_a.py::Derived.method"]
    assert method["kind"] == "function"
    assert method["is_method"] is True
    assert method["parent_id"] == "module_a.py::Derived"

    top_fn = graph.nodes["module_a.py::top_level_function"]
    assert top_fn["is_method"] is False
    assert top_fn["parent_id"] is None

    # ---- contains edges ----
    def has_edge_of_type(u: str, v: str, edge_type: str) -> bool:
        if not graph.has_edge(u, v):
            return False
        return any(data["type"] == edge_type for data in graph[u][v].values())

    # module -> class
    assert has_edge_of_type("module_a.py", "module_a.py::Base", "contains")
    assert has_edge_of_type("module_a.py", "module_a.py::Derived", "contains")

    # module -> module-level function
    assert has_edge_of_type("module_a.py", "module_a.py::top_level_function", "contains")

    # class -> method
    assert has_edge_of_type("module_a.py::Derived", "module_a.py::Derived.method", "contains")

    # module -> method should NOT exist (method belongs to class, not module)
    assert not graph.has_edge("module_a.py", "module_a.py::Derived.method")

    # ---- inherits edges ----
    assert has_edge_of_type("module_a.py::Derived", "module_a.py::Base", "inherits")

    # module_b's Unrelated inherits "Base", but Base isn't defined in module_b
    # -> must NOT produce an edge (same-module-only resolution)
    unrelated_out_edges = list(graph.out_edges("module_b.py::Unrelated", data=True))
    inherits_edges = [d for _, _, d in unrelated_out_edges if d["type"] == "inherits"]
    assert len(inherits_edges) == 0, "cross-module inherits edge should not be created"

    # ---- edge directions ----
    # inherits edge points subclass -> base class
    assert graph.has_edge("module_a.py::Derived", "module_a.py::Base")
    assert not graph.has_edge("module_a.py::Base", "module_a.py::Derived")

    print("All assertions passed.")
    print(f"  module nodes:   {len(modules)}")
    print(f"  class nodes:    {len(classes)}")
    print(f"  function nodes: {len(functions)}")
    print(f"  total edges:    {graph.number_of_edges()}")


if __name__ == "__main__":
    main()