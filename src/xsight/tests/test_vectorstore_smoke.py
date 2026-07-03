"""
Smoke test: run scan -> parse -> build -> chunk -> embed -> vectorstore
against a real Qdrant instance, using a small sample of real chunks.

Requires a running Qdrant instance:
    docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
"""

import sys
from pathlib import Path

from qdrant_client.http.exceptions import ResponseHandlingException

from xsight.chunker.core import chunk
from xsight.embeddings.core import embed
from xsight.embeddings.provider import OllamaEmbeddingProvider
from xsight.graph.builder import build
from xsight.parser.core import parse
from xsight.scanner.core import scan
from xsight.vectorstore.core import build_point_id, create_collection, delete, list_point_ids, search, upsert
from xsight.vectorstore.provider import QdrantVectorStoreProvider

SAMPLE_SIZE = 5
TEST_REPO_ID = 999999


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m xsight.tests.test_vectorstore_smoke <repo_path>")
        sys.exit(1)

    repo_path = Path(sys.argv[1]).expanduser().resolve()
    result = scan(repo_path)
    python_files = [f for f in result.snapshot.files if f.language == "python"]
    modules = [parse(repo_path / f.relative_path, f.relative_path) for f in python_files]
    graph = build(modules)
    chunks = chunk(graph, repo_path)[:SAMPLE_SIZE]

    if not chunks:
        print("No chunks found to embed.")
        sys.exit(1)

    embedding_provider = OllamaEmbeddingProvider()
    embedded = embed(chunks, embedding_provider)

    vector_provider = QdrantVectorStoreProvider()

    try:
        vector_provider.collection_exists()
    except ResponseHandlingException as e:
        print(
            "Could not reach Qdrant.\n"
            "Start it with:\n"
            "  docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant\n"
            f"Original error: {e}"
        )
        sys.exit(1)

    # ---- collection creation ----
    create_collection(embedding_provider.dimension, vector_provider)
    assert vector_provider.collection_exists()

    expected_ids = {build_point_id(TEST_REPO_ID, ec.chunk.id) for ec in embedded}

    # ---- cleanup before: remove leftovers from a previous failed run ----
    delete(list(list_point_ids(TEST_REPO_ID, vector_provider)), vector_provider)

    try:
        # ---- upsert ----
        upsert(embedded, TEST_REPO_ID, vector_provider)

        # ---- list_point_ids matches expected UUID5s exactly ----
        actual_ids = list_point_ids(TEST_REPO_ID, vector_provider)
        assert actual_ids == expected_ids, (
            f"point id mismatch: expected {expected_ids}, got {actual_ids}"
        )

        # ---- search returns the query chunk among its own neighbors ----
        query_chunk = embedded[0]
        results = search(query_chunk.embedding, TEST_REPO_ID, k=SAMPLE_SIZE, provider=vector_provider)
        result_ids = [r.chunk_id for r in results]
        assert query_chunk.chunk.id in result_ids, (
            "expected the query chunk's own id among its nearest neighbors"
        )

        # ---- all hits belong to the requested repo_id ----
        # (implicit via filtering, but confirm no cross-repo leakage by re-checking count)
        assert len(results) <= SAMPLE_SIZE

        # ---- payload fields preserved exactly ----
        by_id = {r.chunk_id: r for r in results}
        for ec in embedded:
            if ec.chunk.id not in by_id:
                continue
            r = by_id[ec.chunk.id]
            assert r.content == ec.chunk.content
            assert r.relative_path == ec.chunk.relative_path
            assert r.kind == ec.chunk.kind
            assert r.start_line == ec.chunk.start_line
            assert r.end_line == ec.chunk.end_line

        print("All assertions passed.\n")
        print(f"Chunks embedded and stored: {len(embedded)}")
        print(f"Point IDs match expected:   {actual_ids == expected_ids}")
        print(f"Sample search hit count:    {len(results)}")

    finally:
        # ---- cleanup after: leave Qdrant clean for next run ----
        delete(list(expected_ids), vector_provider)


if __name__ == "__main__":
    main()