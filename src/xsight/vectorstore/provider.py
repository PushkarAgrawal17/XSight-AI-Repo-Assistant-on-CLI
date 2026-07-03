from typing import Protocol

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from xsight.vectorstore.models import PointRecord


class VectorStoreProvider(Protocol):
    """Provider-agnostic vector store operations. Deliberately expressed in
    terms of our own PointRecord, not any specific vector DB's SDK types,
    so no provider-specific shapes leak into core.py."""

    def collection_exists(self) -> bool: ...

    def create_collection(self, vector_size: int) -> None: ...

    def upsert(self, points: list[PointRecord]) -> None: ...

    def delete(self, point_ids: list[str]) -> None: ...

    def query(self, vector: list[float], repo_id: int, limit: int) -> list[PointRecord]:
        """Return the top `limit` closest points for `repo_id`, each carrying
        its similarity score under payload["_score"]."""
        ...

    def list_ids(self, repo_id: int) -> set[str]: ...


class QdrantVectorStoreProvider:
    """VectorStoreProvider backed by a local/remote Qdrant instance."""

    def __init__(
        self,
        collection_name: str = "xsight_chunks",
        url: str = "http://localhost:6333",
    ) -> None:
        self._collection_name = collection_name
        self._client = QdrantClient(url=url)

    def collection_exists(self) -> bool:
        return self._client.collection_exists(self._collection_name)

    def create_collection(self, vector_size: int) -> None:
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="repo_id",
            field_schema="integer",
        )

    def upsert(self, points: list[PointRecord]) -> None:
        self._client.upsert(
            collection_name=self._collection_name,
            points=[
                PointStruct(id=p.id, vector=p.vector, payload=p.payload) for p in points
            ],
        )

    def delete(self, point_ids: list[str]) -> None:
        self._client.delete(
            collection_name=self._collection_name,
            points_selector=point_ids,
        )

    def query(self, vector: list[float], repo_id: int, limit: int) -> list[PointRecord]:
        result = self._client.query_points(
            collection_name=self._collection_name,
            query=vector,
            query_filter=Filter(
                must=[FieldCondition(key="repo_id", match=MatchValue(value=repo_id))]
            ),
            limit=limit,
        )
        return [
            PointRecord(
                id=str(point.id),
                vector=[],
                payload=point.payload,
                score=point.score,
            )
            for point in result.points
        ]

    def list_ids(self, repo_id: int) -> set[str]:
        ids: set[str] = set()
        offset = None
        while True:
            points, offset = self._client.scroll(
                collection_name=self._collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="repo_id", match=MatchValue(value=repo_id))]
                ),
                with_payload=False,
                with_vectors=False,
                limit=256,
                offset=offset,
            )
            ids.update(str(p.id) for p in points)
            if offset is None:
                break
        return ids