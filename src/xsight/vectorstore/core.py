import uuid

from xsight.embeddings.models import EmbeddedChunk
from xsight.vectorstore.models import PointRecord, SearchResult
from xsight.vectorstore.provider import VectorStoreProvider

# Fixed namespace so point IDs are deterministic across runs/machines.
_POINT_ID_NAMESPACE = uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")


def build_point_id(repo_id: int, chunk_id: str) -> str:
    """Derive a deterministic Qdrant-compatible point ID from our own
    canonical Chunk.id, scoped by repo_id so identical chunk IDs across
    different repositories (sharing one global collection) never collide."""
    return str(uuid.uuid5(_POINT_ID_NAMESPACE, f"{repo_id}:{chunk_id}"))


def create_collection(vector_size: int, provider: VectorStoreProvider) -> None:
    """Idempotent: does nothing if the collection already exists."""
    if not provider.collection_exists():
        provider.create_collection(vector_size)


def upsert(chunks: list[EmbeddedChunk], repo_id: int, provider: VectorStoreProvider) -> None:
    if not chunks:
        return

    points = [
        PointRecord(
            id=build_point_id(repo_id, ec.chunk.id),
            vector=ec.embedding,
            payload={
                "chunk_id": ec.chunk.id,
                "repo_id": repo_id,
                "relative_path": ec.chunk.relative_path,
                "kind": ec.chunk.kind,
                "start_line": ec.chunk.start_line,
                "end_line": ec.chunk.end_line,
                "content": ec.chunk.content,
            },
        )
        for ec in chunks
    ]
    provider.upsert(points)


def delete(point_ids: list[str], provider: VectorStoreProvider) -> None:
    if not point_ids:
        return
    provider.delete(point_ids)


def search(
    query_vector: list[float], repo_id: int, k: int, provider: VectorStoreProvider
) -> list[SearchResult]:
    points = provider.query(query_vector, repo_id, k)
    return [
        SearchResult(
            chunk_id=p.payload["chunk_id"],
            content=p.payload["content"],
            relative_path=p.payload["relative_path"],
            kind=p.payload["kind"],
            start_line=p.payload["start_line"],
            end_line=p.payload["end_line"],
            score=p.score,
        )
        for p in points
    ]


def list_point_ids(repo_id: int, provider: VectorStoreProvider) -> set[str]:
    return provider.list_ids(repo_id)