"""
Smoke test for retrieval.search().

Runs real semantic retrieval against a real Ollama embedding provider and
a real, already-indexed Qdrant collection. Validates API invariants
(non-empty results, payload completeness, descending score order) --
not semantic relevance, which is a human sanity check via the printed
ranked list. No exception handling: fails loudly if Ollama or Qdrant is
unreachable, consistent with every other smoke test.

Usage:
    uv run python -m xsight.tests.test_retrieval_smoke <repo_path>

The given repo must already be indexed (via `xsight init`) before running.
"""

import sys
from pathlib import Path

from xsight.config.settings import settings
from xsight.database.connection import get_connection
from xsight.database.repositories import get_or_create_repository
from xsight.embeddings.provider import OllamaEmbeddingProvider
from xsight.retrieval.core import search
from xsight.vectorstore.provider import QdrantVectorStoreProvider

QUERY = "how does repository scanning work"
K = 5


def test_search_smoke(repo_path: Path) -> None:
    embedding_provider = OllamaEmbeddingProvider(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
    vectorstore_provider = QdrantVectorStoreProvider(
        collection_name=settings.qdrant_collection,
        url=settings.qdrant_url,
    )

    conn = get_connection()
    repo_id = get_or_create_repository(repo_path, conn)
    conn.close()

    results = search(
        query=QUERY,
        repo_id=repo_id,
        k=K,
        embedding_provider=embedding_provider,
        vectorstore_provider=vectorstore_provider,
    )

    assert len(results) > 0
    assert len(results) <= K
    assert all(result.content for result in results)
    assert all(result.relative_path for result in results)
    assert all(result.score is not None for result in results)
    assert all(result.relative_path.endswith(".py") for result in results)
    assert all(
        results[i].score >= results[i + 1].score
        for i in range(len(results) - 1)
    )

    print(f"Query: {QUERY}\n")
    for i, result in enumerate(results, start=1):
        print(f"{i}. {result.relative_path} (score: {result.score:.2f})")

    print("\ntest_search_smoke passed")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python -m xsight.tests.test_retrieval_smoke <repo_path>")
        sys.exit(1)

    resolved_path = Path(sys.argv[1]).expanduser().resolve()
    test_search_smoke(resolved_path)