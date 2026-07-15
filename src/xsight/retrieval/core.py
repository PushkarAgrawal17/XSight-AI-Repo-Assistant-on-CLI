from pathlib import Path

import networkx as nx

from xsight.chunker.core import chunk_one
from xsight.embeddings.provider import EmbeddingProvider
from xsight.vectorstore import core as vectorstore
from xsight.vectorstore.models import SearchResult
from xsight.vectorstore.provider import VectorStoreProvider


def search(
    query: str,
    repo_id: int,
    k: int,
    embedding_provider: EmbeddingProvider,
    vectorstore_provider: VectorStoreProvider,
) -> list[SearchResult]:
    """
    Perform semantic retrieval for a natural-language query.
    ...
    (unchanged)
    """
    query_vector = embedding_provider.embed([query])[0]
    return vectorstore.search(query_vector, repo_id, k, vectorstore_provider)


def _symbolic_matches(
    query: str, graph: nx.MultiDiGraph, repo_path: Path
) -> list[SearchResult]:
    """Find function/method nodes whose name lexically matches the query.

    Case-insensitive substring match, checked both directions (query token
    in name, or name in query). No fuzzy matching -- unmatched names are
    simply skipped rather than guessed at.

    score is a fixed low sentinel (0.0), not a real similarity measure --
    symbolic hits are ranked purely by interleave position in
    search_hybrid(), never by comparing this score against vector scores.
    """
    query_lower = query.lower()
    tokens = [t for t in query_lower.split() if t]

    matches: list[tuple[str, int]] = []  # (node_id, name_start_index) for deterministic sort
    for node_id, data in graph.nodes(data=True):
        if data["kind"] != "function":
            continue
        name_lower = data["name"].lower()
        hit = any(tok in name_lower for tok in tokens) or name_lower in query_lower
        if hit:
            positions = [name_lower.find(tok) for tok in tokens if tok in name_lower]
            sort_key = min(positions) if positions else 0
            matches.append((node_id, sort_key))

    matches.sort(key=lambda pair: (pair[1], pair[0]))

    results = []
    for node_id, _ in matches:
        chunk = chunk_one(graph, repo_path, node_id)
        results.append(
            SearchResult(
                chunk_id=chunk.id,
                content=chunk.content,
                relative_path=chunk.relative_path,
                kind=chunk.kind,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                score=0.0,
            )
        )
    return results


def search_hybrid(
    query: str,
    repo_id: int,
    k: int,
    graph: nx.MultiDiGraph,
    repo_path: Path,
    embedding_provider: EmbeddingProvider,
    vectorstore_provider: VectorStoreProvider,
) -> list[SearchResult]:
    """
    Hybrid retrieval: combines semantic vector search with a lexical scan
    over function/method names in the repository graph.

    Vector and symbolic hits are NOT scored on a common scale -- vector
    scores are cosine similarities, symbolic hits have no comparable
    signal. Instead of merging by score, results are interleaved by each
    list's own internal ranking (vector search's relevance order, and
    symbolic matches' name-match order), deduplicating by chunk_id as
    entries are collected. This preserves within-list ordering, which is
    meaningful, without asserting a cross-list ordering, which isn't.

    Stops once k unique results are collected. Falls back gracefully if
    either list is shorter than k or empty.
    """
    vector_hits = search(
        query=query,
        repo_id=repo_id,
        k=k,
        embedding_provider=embedding_provider,
        vectorstore_provider=vectorstore_provider,
    )
    symbolic_hits = _symbolic_matches(query, graph, repo_path)

    seen: set[str] = set()
    combined: list[SearchResult] = []

    i, j = 0, 0
    while len(combined) < k and (i < len(vector_hits) or j < len(symbolic_hits)):
        if i < len(vector_hits):
            candidate = vector_hits[i]
            i += 1
            if candidate.chunk_id not in seen:
                seen.add(candidate.chunk_id)
                combined.append(candidate)
                if len(combined) >= k:
                    break
        if j < len(symbolic_hits):
            candidate = symbolic_hits[j]
            j += 1
            if candidate.chunk_id not in seen:
                seen.add(candidate.chunk_id)
                combined.append(candidate)

    return combined