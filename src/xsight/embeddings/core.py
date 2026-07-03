from xsight.chunker.models import Chunk
from xsight.embeddings.models import EmbeddedChunk
from xsight.embeddings.provider import EmbeddingProvider


def embed(chunks: list[Chunk], provider: EmbeddingProvider) -> list[EmbeddedChunk]:
    if not chunks:
        return []

    vectors = provider.embed([c.content for c in chunks])
    assert len(vectors) == len(chunks), (
        f"provider returned {len(vectors)} vectors for {len(chunks)} chunks"
    )

    return [EmbeddedChunk(chunk=c, embedding=v) for c, v in zip(chunks, vectors)]