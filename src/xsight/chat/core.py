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
from xsight.embeddings.provider import EmbeddingProvider
from xsight.expansion.core import expand
from xsight.llm.provider import GeminiLLMProvider
from xsight.retrieval.core import search_hybrid
from xsight.vectorstore.provider import VectorStoreProvider

DEFAULT_K = 5


class NoResultsError(Exception):
    """Raised when semantic retrieval finds no indexed chunks for the query."""


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