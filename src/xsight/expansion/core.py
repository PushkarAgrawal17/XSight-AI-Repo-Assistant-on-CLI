import networkx as nx

from xsight.expansion.models import ExpandedResult, RelatedSymbol
from xsight.vectorstore.models import SearchResult

MAX_HOPS = 2
MAX_RELATED = 10

def _related_symbol(graph: nx.MultiDiGraph, node_id: str) -> RelatedSymbol:
    data = graph.nodes[node_id]
    return RelatedSymbol(
        name=data["name"],
        kind=data["kind"],
        start_line=data["start_line"],
        end_line=data["end_line"],
    )


def _resolve_owner(graph: nx.MultiDiGraph, node_id: str) -> str:
    owners = [
        u for u, _, d in graph.in_edges(node_id, data=True) if d["type"] == "contains"
    ]
    assert len(owners) == 1, f"{node_id} has {len(owners)} contains-owners: {owners}"
    return owners[0]

def _bfs_calls(graph: nx.MultiDiGraph, start_id: str, reverse: bool) -> list[RelatedSymbol]:
    """BFS over `calls` edges (or their reverse, for called_by) up to
    MAX_HOPS, collecting at most MAX_RELATED symbols.

    Deterministic: each BFS level is deduped into a set, then sorted by
    node_id before being used as the next frontier or appended to the
    result -- output never depends on graph/dict iteration order. A single
    visited set (seeded with start_id) prevents cycles from looping.
    """
    visited = {start_id}
    frontier = [start_id]
    collected: list[str] = []

    for _ in range(MAX_HOPS):
        next_frontier: set[str] = set()
        for node_id in frontier:
            edges = graph.in_edges(node_id, data=True) if reverse else graph.out_edges(node_id, data=True)
            for u, v, d in edges:
                if d["type"] != "calls":
                    continue
                neighbor_id = u if reverse else v
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    next_frontier.add(neighbor_id)

        level_sorted = sorted(next_frontier)
        for node_id in level_sorted:
            if len(collected) >= MAX_RELATED:
                return [_related_symbol(graph, nid) for nid in collected]
            collected.append(node_id)

        frontier = level_sorted
        if not frontier:
            break

    return [_related_symbol(graph, nid) for nid in collected]

def _expand_one(graph: nx.MultiDiGraph, hit: SearchResult) -> ExpandedResult:
    # KeyError propagates here if hit.chunk_id isn't a graph node -- intentional,
    # per the fail-loudly convention. Not caught or defaulted.
    owner_id = _resolve_owner(graph, hit.chunk_id)
    owner_kind = graph.nodes[owner_id]["kind"]
    assert owner_kind in ("module", "class"), (
        f"unexpected owner kind '{owner_kind}' for {owner_id}"
    )

    parent = None
    base_class = None

    if owner_kind == "class":
        parent = _related_symbol(graph, owner_id)

        base_class_targets = [
            v for _, v, d in graph.out_edges(owner_id, data=True) if d["type"] == "inherits"
        ]
        if base_class_targets:
            base_class = _related_symbol(graph, base_class_targets[0])

    sibling_ids = [
        v
        for _, v, d in graph.out_edges(owner_id, data=True)
        if d["type"] == "contains"
        and graph.nodes[v]["kind"] == "function"
        and v != hit.chunk_id
    ]
    sibling_ids.sort(key=lambda node_id: graph.nodes[node_id]["start_line"])
    siblings = [_related_symbol(graph, node_id) for node_id in sibling_ids]

    calls = _bfs_calls(graph, hit.chunk_id, reverse=False)
    called_by = _bfs_calls(graph, hit.chunk_id, reverse=True)
    
    return ExpandedResult(
        hit=hit,
        parent=parent,
        siblings=siblings,
        base_class=base_class,
        calls=calls,
        called_by=called_by,
    )

def expand(hits: list[SearchResult], graph: nx.MultiDiGraph) -> list[ExpandedResult]:
    """
    Expand each retrieval hit with its one-hop structural neighborhood:
    parent class (if the hit is a method), sibling functions/methods in the
    same container, same-module base class (if present), and direct
    caller/callee functions via "calls" edges (same-module or cross-module).

    Purely graph-driven: never infers relationships from names or source
    text, never reads source files, never mutates the graph. Traversal is
    deterministic -- the same hits always produce the same expansion.

    Output order matches input order; expansion adds context per hit
    without re-ranking. Raises KeyError if a hit's chunk_id is not present
    in the graph (e.g. stale index vs. current source) -- not caught here.
    """
    return [_expand_one(graph, hit) for hit in hits]