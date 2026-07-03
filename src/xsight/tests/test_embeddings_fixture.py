"""
Deterministic embeddings pipeline test.

Uses a fake in-memory provider (satisfies EmbeddingProvider via structural
typing) so this test never touches Ollama or the network.
"""

from xsight.chunker.models import Chunk
from xsight.embeddings.core import embed


class FakeEmbeddingProvider:
    """Deterministic fake: each text maps to a fixed-length vector derived
    from its length, so output is easy to predict and assert against."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(len(t)), 0.0, 1.0] for t in texts]


def _make_chunk(id_: str, content: str) -> Chunk:
    return Chunk(
        id=id_,
        kind="function",
        content=content,
        relative_path="fake.py",
        start_line=1,
        end_line=2,
    )


def main() -> None:
    chunk_a = _make_chunk("fake.py::a", "short")
    chunk_b = _make_chunk("fake.py::b", "a bit longer content")
    provider = FakeEmbeddingProvider()

    # ---- normal case ----
    result = embed([chunk_a, chunk_b], provider)

    assert len(result) == 2
    assert result[0].chunk is chunk_a
    assert result[1].chunk is chunk_b
    assert result[0].embedding == [float(len(chunk_a.content)), 0.0, 1.0]
    assert result[1].embedding == [float(len(chunk_b.content)), 0.0, 1.0]

    # provider called exactly once, with content in input order
    assert provider.calls == [[chunk_a.content, chunk_b.content]]

    # ---- empty input: must not call the provider at all ----
    provider_2 = FakeEmbeddingProvider()
    empty_result = embed([], provider_2)
    assert empty_result == []
    assert provider_2.calls == [], "provider should not be called for empty input"

    print("All assertions passed.")


if __name__ == "__main__":
    main()