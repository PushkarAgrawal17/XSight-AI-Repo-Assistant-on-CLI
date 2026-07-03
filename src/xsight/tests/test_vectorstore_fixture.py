"""
Deterministic vectorstore pipeline test.

Uses a fake in-memory provider (satisfies VectorStoreProvider via
structural typing) so this test never touches a real Qdrant instance.
Proves core.py's orchestration (ID derivation, payload construction,
result translation) -- not real vector similarity, which is Qdrant's job
and is covered by the smoke test instead.
"""

from xsight.chunker.models import Chunk
from xsight.embeddings.models import EmbeddedChunk
from xsight.vectorstore.core import build_point_id, create_collection, delete, list_point_ids, search, upsert
from xsight.vectorstore.models import PointRecord


class FakeVectorStoreProvider:
    def __init__(self) -> None:
        self._store: dict[str, PointRecord] = {}
        self.collection_created = False
        self.create_collection_calls = 0
        self.upsert_calls = 0
        self.delete_calls = 0

    def collection_exists(self) -> bool:
        return self.collection_created

    def create_collection(self, vector_size: int) -> None:
        self.collection_created = True
        self.create_collection_calls += 1

    def upsert(self, points: list[PointRecord]) -> None:
        self.upsert_calls += 1
        for p in points:
            self._store[p.id] = p

    def delete(self, point_ids: list[str]) -> None:
        self.delete_calls += 1
        for pid in point_ids:
            self._store.pop(pid, None)

    def query(self, vector: list[float], repo_id: int, limit: int) -> list[PointRecord]:
        matches = [p for p in self._store.values() if p.payload["repo_id"] == repo_id]
        return [
            PointRecord(id=p.id, vector=[], payload={**p.payload, "_score": 1.0})
            for p in matches[:limit]
        ]

    def list_ids(self, repo_id: int) -> set[str]:
        return {p.id for p in self._store.values() if p.payload["repo_id"] == repo_id}


def _make_chunk(id_: str, content: str = "content") -> Chunk:
    return Chunk(
        id=id_, kind="function", content=content,
        relative_path="fake.py", start_line=1, end_line=2,
    )


def main() -> None:
    ec_a = EmbeddedChunk(chunk=_make_chunk("fake.py::a", "content a"), embedding=[0.1, 0.2])
    ec_b = EmbeddedChunk(chunk=_make_chunk("fake.py::b", "content b"), embedding=[0.3, 0.4])
    ec_c_other_repo = EmbeddedChunk(chunk=_make_chunk("fake.py::c", "content c"), embedding=[0.5, 0.6])

    # ---- create_collection idempotency ----
    provider = FakeVectorStoreProvider()
    create_collection(768, provider)
    create_collection(768, provider)
    assert provider.collection_created is True
    assert provider.create_collection_calls == 1, "create_collection should only hit provider once"

    # ---- upsert stores every chunk ----
    upsert([ec_a, ec_b], repo_id=1, provider=provider)
    upsert([ec_c_other_repo], repo_id=2, provider=provider)
    assert len(provider._store) == 3

    # ---- point IDs are exactly the expected deterministic UUID5s ----
    expected_ids_repo1 = {
        build_point_id(1, ec_a.chunk.id),
        build_point_id(1, ec_b.chunk.id),
    }
    assert list_point_ids(1, provider) == expected_ids_repo1

    # ---- delete removes only the requested point ----
    id_a = build_point_id(1, ec_a.chunk.id)
    delete([id_a], provider)
    assert list_point_ids(1, provider) == {build_point_id(1, ec_b.chunk.id)}

    # ---- search respects repo_id filtering ----
    results = search(query_vector=[0.0, 0.0], repo_id=2, k=10, provider=provider)
    assert len(results) == 1
    assert results[0].chunk_id == "fake.py::c"

    # ---- SearchResult preserves payload correctly ----
    r = results[0]
    assert r.content == "content c"
    assert r.relative_path == "fake.py"
    assert r.kind == "function"
    assert r.start_line == 1 and r.end_line == 2
    assert isinstance(r.score, float)

    # ---- empty inputs: no crashes, no unnecessary provider calls ----
    provider2 = FakeVectorStoreProvider()
    upsert([], repo_id=1, provider=provider2)
    delete([], provider=provider2)
    assert provider2.upsert_calls == 0, "upsert should not call provider for empty input"
    assert provider2.delete_calls == 0, "delete should not call provider for empty input"

    print("All assertions passed.")


if __name__ == "__main__":
    main()