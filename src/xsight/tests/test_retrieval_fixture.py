"""
Fixture test for retrieval.search().

Validates orchestration only: that retrieval.search() embeds the query
exactly once, passes the resulting vector (not the raw string) and the
repo_id/k arguments unchanged into vectorstore.core.search(), and returns
its result without transformation. Does NOT validate embedding quality,
vector similarity, or ranking -- those are covered elsewhere (embeddings
and vectorstore fixtures). Real semantic retrieval against Ollama and
Qdrant is validated separately by the smoke test.
"""

from xsight.retrieval.core import search
from xsight.vectorstore.models import PointRecord


class FakeEmbeddingProvider:
    def __init__(self, fixed_vector: list[float]):
        self._fixed_vector = fixed_vector
        self.calls: list[list[str]] = []

    @property
    def dimension(self) -> int:
        return len(self._fixed_vector)

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [self._fixed_vector for _ in texts]


class FakeVectorStoreProvider:
    def __init__(self, canned_results: list[PointRecord]):
        self._canned_results = canned_results
        self.query_calls: list[tuple[list[float], int, int]] = []

    def query(self, vector: list[float], repo_id: int, limit: int) -> list[PointRecord]:
        self.query_calls.append((vector, repo_id, limit))
        return self._canned_results

    def collection_exists(self) -> bool:
        raise NotImplementedError

    def create_collection(self, vector_size: int) -> None:
        raise NotImplementedError

    def upsert(self, points: list[PointRecord]) -> None:
        raise NotImplementedError

    def delete(self, point_ids: list[str]) -> None:
        raise NotImplementedError

    def list_ids(self, repo_id: int) -> set[str]:
        raise NotImplementedError


def test_search_orchestration() -> None:
    fixed_vector = [0.1, 0.2, 0.3]
    query = "how does the scanner detect binary files"
    repo_id = 7
    k = 3

    canned_points = [
        PointRecord(
            id="point-1",
            vector=[],
            payload={
                "chunk_id": "scanner/core.py::is_binary",
                "repo_id": repo_id,
                "relative_path": "scanner/core.py",
                "kind": "function",
                "start_line": 10,
                "end_line": 20,
                "content": "def is_binary(...): ...",
            },
        ),
    ]

    fake_embedding = FakeEmbeddingProvider(fixed_vector)
    fake_vectorstore = FakeVectorStoreProvider(canned_points)

    result = search(
        query=query,
        repo_id=repo_id,
        k=k,
        embedding_provider=fake_embedding,
        vectorstore_provider=fake_vectorstore,
    )

    # Embedding provider called exactly once, with the query wrapped in a list
    assert len(fake_embedding.calls) == 1
    assert fake_embedding.calls[0] == [query]

    # Vectorstore queried exactly once
    assert len(fake_vectorstore.query_calls) == 1

    vector, queried_repo_id, queried_k = fake_vectorstore.query_calls[0]
    assert vector == fixed_vector
    assert queried_repo_id == repo_id
    assert queried_k == k

    # Result is whatever vectorstore.core.search() produced, unchanged
    assert len(result) == 1
    assert result[0].chunk_id == "scanner/core.py::is_binary"
    assert result[0].relative_path == "scanner/core.py"

    print("test_search_orchestration passed")


if __name__ == "__main__":
    test_search_orchestration()