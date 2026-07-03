"""
Smoke test: run the real OllamaEmbeddingProvider against a small subset
of chunks from a real repository.

Requires a running Ollama instance with nomic-embed-text pulled:
    ollama serve
    ollama pull nomic-embed-text
"""

import math
import sys
from pathlib import Path

import requests

from xsight.chunker.core import chunk
from xsight.embeddings.core import embed
from xsight.embeddings.provider import OllamaEmbeddingProvider
from xsight.graph.builder import build
from xsight.parser.core import parse
from xsight.scanner.core import scan

SAMPLE_SIZE = 5


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m xsight.tests.test_embeddings_smoke <repo_path>")
        sys.exit(1)

    repo_path = Path(sys.argv[1]).expanduser().resolve()
    result = scan(repo_path)
    python_files = [f for f in result.snapshot.files if f.language == "python"]

    modules = [
        parse(repo_path / f.relative_path, f.relative_path) for f in python_files
    ]
    graph = build(modules)
    chunks = chunk(graph, repo_path)[:SAMPLE_SIZE]

    if not chunks:
        print("No chunks found to embed.")
        sys.exit(1)

    provider = OllamaEmbeddingProvider()

    try:
        embedded = embed(chunks, provider)
    except requests.ConnectionError as e:
        print(
            "Could not reach Ollama.\n"
            "Make sure it's running and the model is pulled:\n"
            "  ollama serve\n"
            "  ollama pull nomic-embed-text\n"
            f"Original error: {e}"
        )
        sys.exit(1)

    # ---- invariants ----
    assert len(embedded) == len(chunks)

    for ec, original_chunk in zip(embedded, chunks):
        assert ec.chunk is original_chunk, "ordering broken: chunk mismatch"

    dimension = len(embedded[0].embedding)
    assert dimension > 0, "embedding dimension must be non-zero"

    for ec in embedded:
        assert len(ec.embedding) == dimension, (
            f"inconsistent embedding dimension for {ec.chunk.id}: "
            f"expected {dimension}, got {len(ec.embedding)}"
        )
        assert all(math.isfinite(v) for v in ec.embedding), (
            f"non-finite value in embedding for {ec.chunk.id}"
        )

    print("All assertions passed.\n")
    print(f"Model:            {provider.model}")
    print(f"Chunks embedded:  {len(embedded)}")
    print(f"Vector dimension: {dimension}")
    print(f"Sample vector (first 5 dims) for {embedded[0].chunk.id}:")
    print(f"  {embedded[0].embedding[:5]}")


if __name__ == "__main__":
    main()