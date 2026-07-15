"""
Fixture test for search_hybrid(): interleaving, deduplication, and
ordering behavior. The vector half is patched (as in chat.core's fixture
test); the symbolic half runs the real parser/graph/chunker pipeline
against the existing chunker_fixture.py file, so chunk_one() reads real
source from disk.
"""

from pathlib import Path
from unittest.mock import patch

from xsight.graph.builder import build
from xsight.parser.core import parse
from xsight.retrieval.core import search_hybrid
from xsight.vectorstore.models import SearchResult

FIXTURE_DIR = Path(__file__).parent
FIXTURE_FILE = "chunker_fixture.py"


class FakeEmbeddingProvider:
    dimension = 3

    def embed(self, texts):
        return [[0.0, 0.0, 0.0] for _ in texts]


def _build_graph():
    module = parse(FIXTURE_DIR / FIXTURE_FILE, FIXTURE_FILE)
    return build([module])


def main() -> None:
    graph = _build_graph()
    embedding_provider = FakeEmbeddingProvider()

    # Only the vector half of search_hybrid is faked; symbolic matching
    # runs against the real graph/chunk_one path.
    vector_hits = [
        SearchResult(
            chunk_id="chunker_fixture.py::greet",
            content="vector-returned content",
            relative_path="chunker_fixture.py",
            kind="function",
            start_line=1,
            end_line=2,
            score=0.9,
        ),
    ]

    # ---- Case 1: symbolic-only hit surfaces alongside the vector hit ----
    # Query "greeter" lexically matches the class-qualified method name
    # "Greeter.greet" via the name "greet" substring match on the method
    # node, which chunk() does NOT return as "greet" (module fn) confusion
    # -- use a token that only matches the method, not the module function.
    with patch("xsight.retrieval.core.search", return_value=vector_hits):
        results = search_hybrid(
            query="greet",
            repo_id=1,
            k=5,
            graph=graph,
            repo_path=FIXTURE_DIR,
            embedding_provider=embedding_provider,
            vectorstore_provider=None,  # unused, search() is patched
        )

    ids = [r.chunk_id for r in results]
    assert "chunker_fixture.py::greet" in ids, "vector hit should surface"
    assert "chunker_fixture.py::Greeter.greet" in ids, "symbolic hit should surface"

    # ---- Case 2: dedup -- same chunk_id from both vector and symbolic ----
    # "greet" matches both nodes lexically; chunker_fixture.py::greet is
    # also the vector hit above. It must appear exactly once in the output.
    assert ids.count("chunker_fixture.py::greet") == 1, (
        f"expected chunker_fixture.py::greet exactly once, got {ids.count('chunker_fixture.py::greet')}"
    )

    # ---- Case 3: vector hit's own content is preserved (not overwritten
    # by the symbolic scan's re-chunked content for the same id) ----
    greet_result = next(r for r in results if r.chunk_id == "chunker_fixture.py::greet")
    assert greet_result.content == "vector-returned content", (
        "deduped result should keep the first-seen (vector) entry, not be "
        "replaced by the symbolic re-chunk of the same node"
    )

    # ---- Case 4: k limits total unique results ----
    with patch("xsight.retrieval.core.search", return_value=vector_hits):
        limited = search_hybrid(
            query="greet",
            repo_id=1,
            k=1,
            graph=graph,
            repo_path=FIXTURE_DIR,
            embedding_provider=embedding_provider,
            vectorstore_provider=None,
        )
    assert len(limited) == 1, f"expected exactly 1 result with k=1, got {len(limited)}"

    # ---- Case 5: no symbolic match -- vector hits alone still work ----
    with patch("xsight.retrieval.core.search", return_value=vector_hits):
        no_symbolic = search_hybrid(
            query="zzz_no_match_zzz",
            repo_id=1,
            k=5,
            graph=graph,
            repo_path=FIXTURE_DIR,
            embedding_provider=embedding_provider,
            vectorstore_provider=None,
        )
    assert [r.chunk_id for r in no_symbolic] == ["chunker_fixture.py::greet"]

    print("All hybrid retrieval assertions passed.")


    # ---- Case 6: empty/whitespace query does not crash ----
    with patch("xsight.retrieval.core.search", return_value=vector_hits):
        empty_query = search_hybrid(
            query="   ",
            repo_id=1,
            k=5,
            graph=graph,
            repo_path=FIXTURE_DIR,
            embedding_provider=embedding_provider,
            vectorstore_provider=None,
        )
    assert [r.chunk_id for r in empty_query] == ["chunker_fixture.py::greet"]


if __name__ == "__main__":
    main()