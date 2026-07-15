"""
Deterministic BFS test for multi-hop calls/called_by expansion.
Uses a hand-built MultiDiGraph (calls edges aren't produced by
graph_fixture.py's modules), isolating BFS behavior from parsing/graph
building concerns.
"""

import networkx as nx

from xsight.expansion.core import expand
from xsight.vectorstore.models import SearchResult


def _fn_node(graph, node_id, start_line):
    graph.add_node(node_id, kind="function", name=node_id, start_line=start_line, end_line=start_line)


def _build_graph():
    # mod.py: a -> b -> c -> d  (chain, 3 hops)
    #         a -> e            (1 hop, sibling branch)
    #         a -> a            (self-loop / cycle)
    graph = nx.MultiDiGraph()
    graph.add_node("mod.py", kind="module", name="mod", relative_path="mod.py")
    for i, name in enumerate(["a", "b", "c", "d", "e"]):
        _fn_node(graph, f"mod.py::{name}", start_line=i + 1)
        graph.add_edge("mod.py", f"mod.py::{name}", type="contains")

    graph.add_edge("mod.py::a", "mod.py::b", type="calls")
    graph.add_edge("mod.py::b", "mod.py::c", type="calls")
    graph.add_edge("mod.py::c", "mod.py::d", type="calls")  # 3rd hop, must NOT appear (MAX_HOPS=2)
    graph.add_edge("mod.py::a", "mod.py::e", type="calls")
    graph.add_edge("mod.py::a", "mod.py::a", type="calls")  # cycle
    return graph


def _hit(chunk_id):
    return SearchResult(
        chunk_id=chunk_id, content="...", relative_path="mod.py",
        kind="function", start_line=1, end_line=1, score=0.9,
    )


def main() -> None:
    graph = _build_graph()

    expanded = expand([_hit("mod.py::a")], graph)[0]
    call_names = [c.name for c in expanded.calls]

    # 1-hop (b, e) and 2-hop (c) present; 3-hop (d) excluded
    assert set(call_names) == {"mod.py::b", "mod.py::c", "mod.py::e"}, call_names
    assert "mod.py::d" not in call_names, "3rd hop must not be included (MAX_HOPS=2)"

    # cycle (a -> a) must not cause infinite loop or self-inclusion
    assert "mod.py::a" not in call_names, "start node must not appear in its own calls"

    # deterministic ordering: sorted by node_id within each level
    # level 1 = [b, e] sorted -> b, e ; level 2 = [c]
    assert call_names == ["mod.py::b", "mod.py::e", "mod.py::c"], call_names

    # ---- MAX_RELATED truncation ----
    graph2 = nx.MultiDiGraph()
    graph2.add_node("mod.py", kind="module", name="mod", relative_path="mod.py")
    _fn_node(graph2, "mod.py::start", start_line=1)
    graph2.add_edge("mod.py", "mod.py::start", type="contains")
    for i in range(15):
        node_id = f"mod.py::n{i:02d}"
        _fn_node(graph2, node_id, start_line=i + 2)
        graph2.add_edge("mod.py", node_id, type="contains")
        graph2.add_edge("mod.py::start", node_id, type="calls")

    expanded2 = expand([_hit("mod.py::start")], graph2)[0]
    assert len(expanded2.calls) == 10, f"expected MAX_RELATED=10, got {len(expanded2.calls)}"
    assert [c.name for c in expanded2.calls] == sorted(c.name for c in expanded2.calls)

    print("All BFS calls/called_by assertions passed.")


if __name__ == "__main__":
    main()