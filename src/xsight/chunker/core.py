"""Build embeddable chunks from function/method nodes in the repository graph.

Phase 1 scope: chunks are produced only for kind == "function" nodes
(module-level functions and methods). Class and module chunks are
deliberately deferred until the parser IR can express class bodies
excluding nested method definitions.
"""

from pathlib import Path

import networkx as nx

from xsight.chunker.models import Chunk


def chunk(graph: nx.MultiDiGraph, repo_path: Path) -> list[Chunk]:
    """Build chunks for every function/method node in the graph."""
    chunks: list[Chunk] = []

    for node_id, data in graph.nodes(data=True):
        if data["kind"] != "function":
            continue
        chunks.append(_build_chunk(graph, repo_path, node_id, data))

    return chunks


def _build_chunk(
    graph: nx.MultiDiGraph, repo_path: Path, node_id: str, data: dict
) -> Chunk:
    relative_path = _module_of(graph, node_id)
    source = _read_source_slice(repo_path, relative_path, data["start_line"], data["end_line"])
    prefix = _build_prefix(graph, node_id, data, relative_path)

    return Chunk(
        id=node_id,
        kind="function",
        content=f"{prefix}\n{source}",
        relative_path=relative_path,
        start_line=data["start_line"],
        end_line=data["end_line"],
    )


def _module_of(graph: nx.MultiDiGraph, node_id: str) -> str:
    """Find the module a function/method node belongs to by walking its
    single incoming `contains` edge, up to two hops (function -> module,
    or method -> class -> module)."""
    owners = [u for u, _, d in graph.in_edges(node_id, data=True) if d["type"] == "contains"]
    assert len(owners) == 1, f"expected exactly one contains-owner for {node_id}, got {owners}"
    owner_id = owners[0]
    
    owner = graph.nodes[owner_id]
    if owner["kind"] == "module":
        return owner["relative_path"]
    # owner is a class; go up one more level to its module
    return _module_of(graph, owner_id)


def _build_prefix(graph: nx.MultiDiGraph, node_id: str, data: dict, relative_path: str) -> str:
    if data["is_method"]:
        parent_name = graph.nodes[data["parent_id"]]["name"]
        return f"Method: {parent_name}.{data['name']}\nModule: {relative_path}"
    return f"Function: {data['name']}\nModule: {relative_path}"


def _read_source_slice(repo_path: Path, relative_path: str, start_line: int, end_line: int) -> str:
    file_path = repo_path / relative_path
    lines = file_path.read_text(encoding="utf-8").splitlines()
    # start_line/end_line are 1-indexed and inclusive
    return "\n".join(lines[start_line - 1:end_line])