"""Answers a single user question against an already-loaded repository graph.

Owns exactly one responsibility: given a query and pre-built dependencies
(graph, providers), perform retrieval, expansion, prompt construction, and
LLM generation, and return the answer. Contains no loop, no slash-command
handling, no history management, and no console I/O -- those are session/CLI
concerns, not this function's.
"""

from pathlib import Path

import networkx as nx
from google.genai import errors as genai_errors

from xsight.chat.prompt import build_prompt
from xsight.chat.models import ChatTurn
from xsight.chunker.core import chunk_one
from xsight.embeddings.provider import EmbeddingProvider
from xsight.expansion.core import expand
from xsight.llm.provider import GeminiLLMProvider
from xsight.retrieval.core import search_hybrid
from xsight.vectorstore.provider import VectorStoreProvider

DEFAULT_K = 5


class NoResultsError(Exception):
    """Raised when semantic retrieval finds no indexed chunks for the query."""

_NAV_RULES = [
    ("where is", "defined", "definition"),
    ("show implementation of", "", "implementation"),
    ("show me the implementation of", "", "implementation"),
]


def _route(query: str) -> tuple[str, str] | None:
    """Detect an exact navigation query and extract its symbol.

    Deterministic string matching only -- no LLM, no regex. Returns None
    for anything unrecognized, so the caller falls through to hybrid
    retrieval unchanged.
    """
    normalized = query.strip().lower()
    for prefix, suffix, nav_type in sorted(_NAV_RULES, key=lambda r: -len(r[0])):
        if not normalized.startswith(prefix):
            continue
        remainder = query.strip()[len(prefix):].strip().rstrip("?").strip()
        if suffix and remainder.lower().endswith(suffix):
            remainder = remainder[: -len(suffix)].strip()
        if remainder:
            return nav_type, remainder
    return None


def _resolve_symbol(graph: nx.MultiDiGraph, symbol: str) -> list[str]:
    """Resolve a symbol name to matching function/class node ids.

    Qualified names ("Class.method") narrow to methods of that class.
    Bare names match both function and class nodes by name. Never
    guesses -- all matches are returned, ambiguity is the caller's job.
    """
    if "." in symbol:
        class_name, _, member_name = symbol.rpartition(".")
        matches = []
        for node_id, data in graph.nodes(data=True):
            if data["kind"] != "function" or data["name"] != member_name:
                continue
            parent_id = data.get("parent_id")
            if parent_id and graph.nodes[parent_id].get("name") == class_name:
                matches.append(node_id)
        return matches

    return [
        node_id
        for node_id, data in graph.nodes(data=True)
        if data["kind"] in ("function", "class") and data["name"] == symbol
    ]


def _owning_module(graph: nx.MultiDiGraph, node_id: str) -> str:
    """Module relative_path owning a class node (single contains hop)."""
    owners = [u for u, _, d in graph.in_edges(node_id, data=True) if d["type"] == "contains"]
    assert len(owners) == 1, f"{node_id} has {len(owners)} contains-owners: {owners}"
    return graph.nodes[owners[0]]["relative_path"]


def _read_source_slice(repo_path: Path, relative_path: str, start_line: int, end_line: int) -> str:
    """1-indexed, inclusive line-range read. Local to navigation --
    deliberately duplicated from chunker rather than imported, so
    navigation stays independent of chunker internals."""
    file_path = repo_path / relative_path
    lines = file_path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[start_line - 1:end_line])


def _class_facts(graph: nx.MultiDiGraph, repo_path: Path, node_id: str, include_source: bool) -> str:
    data = graph.nodes[node_id]
    relative_path = _owning_module(graph, node_id)
    lines = [
        f"Class:\n{data['name']}",
        f"Location:\n{relative_path} lines {data['start_line']}-{data['end_line']}",
    ]
    if include_source:
        source = _read_source_slice(repo_path, relative_path, data["start_line"], data["end_line"])
        lines.append(f"Source:\n{source}")
    return "\n\n".join(lines)


def _function_facts(graph: nx.MultiDiGraph, repo_path: Path, node_id: str, include_source: bool) -> str:
    data = graph.nodes[node_id]
    result = chunk_one(graph, repo_path, node_id)
    label = "Method" if data["is_method"] else "Function"
    lines = [
        f"{label}:\n{data['name']}",
        f"Location:\n{result.relative_path} lines {result.start_line}-{result.end_line}",
    ]
    if include_source:
        lines.append(f"Source:\n{result.content}")
    return "\n\n".join(lines)


def _symbol_facts(graph: nx.MultiDiGraph, repo_path: Path, node_ids: list[str], include_source: bool) -> str:
    """Facts block for one or more resolved matches. Dispatches per node
    by kind. Multiple matches are concatenated, never narrowed to one --
    the prompt instructs the model to present them as options."""
    blocks = []
    for node_id in node_ids:
        if graph.nodes[node_id]["kind"] == "class":
            blocks.append(_class_facts(graph, repo_path, node_id, include_source))
        else:
            blocks.append(_function_facts(graph, repo_path, node_id, include_source))
    return "\n\n---\n\n".join(blocks)


_NAV_INSTRUCTIONS = (
    "Answer the user's question using only the repository facts below.\n"
    "Do not invent any additional information.\n"
    "If multiple facts are shown, they are all matches for the symbol -- "
    "present them as options rather than picking one."
)


def _build_navigation_prompt(query: str, facts: str) -> str:
    return f"User asked:\n{query}\n\nRepository facts:\n\n{facts}\n\n{_NAV_INSTRUCTIONS}"


def _try_navigation(
    query: str, graph: nx.MultiDiGraph, repo_path: Path, llm_provider: GeminiLLMProvider
) -> str | None:
    """Answer an exact navigation query directly from the graph, or return
    None (unrecognized pattern, or symbol not found) so the caller falls
    through to hybrid retrieval."""
    routed = _route(query)
    if routed is None:
        return None
    nav_type, symbol = routed

    node_ids = _resolve_symbol(graph, symbol)
    if not node_ids:
        return None

    facts = _symbol_facts(graph, repo_path, node_ids, include_source=(nav_type == "implementation"))
    return llm_provider.generate(_build_navigation_prompt(query, facts))

def answer_question(
    query: str,
    repo_id: int,
    graph: nx.MultiDiGraph,
    repo_path: Path,
    embedding_provider: EmbeddingProvider,
    vectorstore_provider: VectorStoreProvider,
    llm_provider: GeminiLLMProvider,
    k: int = DEFAULT_K,
    history: list[ChatTurn] | None = None,
    repo_summary: str | None = None,
) -> str:
    """Answer one question. Raises NoResultsError if retrieval finds
    nothing, and lets genai_errors.APIError propagate on LLM failure --
    both are the caller's responsibility to handle/present."""

    nav_answer = _try_navigation(query, graph, repo_path, llm_provider)
    if nav_answer is not None:
        return nav_answer
    
    results = search_hybrid(
        query=query,
        repo_id=repo_id,
        k=k,
        graph=graph,
        repo_path=repo_path,
        embedding_provider=embedding_provider,
        vectorstore_provider=vectorstore_provider,
    )
    if not results:
        raise NoResultsError(query)

    expanded = expand(results, graph)
    prompt = build_prompt(query, expanded, history, repo_summary)
    return llm_provider.generate(prompt)