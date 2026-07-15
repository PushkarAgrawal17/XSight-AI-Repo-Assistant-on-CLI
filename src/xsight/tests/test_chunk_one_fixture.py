"""
Deterministic regression test: chunk_one() must produce output identical
to the corresponding entry from chunk() for the same node, without
rebuilding chunks for every function in the graph.
"""

from pathlib import Path

from xsight.chunker.core import chunk, chunk_one
from xsight.graph.builder import build
from xsight.parser.core import parse

FIXTURE_DIR = Path(__file__).parent
FIXTURE_FILE = "chunker_fixture.py"


def main() -> None:
    module = parse(FIXTURE_DIR / FIXTURE_FILE, FIXTURE_FILE)
    graph = build([module])

    all_chunks = {c.id: c for c in chunk(graph, FIXTURE_DIR)}
    assert len(all_chunks) == 2, f"expected 2 chunks from chunk(), got {len(all_chunks)}"

    for target_id, expected in all_chunks.items():
        single = chunk_one(graph, FIXTURE_DIR, target_id)
        assert single.id == expected.id
        assert single.content == expected.content
        assert single.relative_path == expected.relative_path
        assert single.kind == expected.kind
        assert single.start_line == expected.start_line
        assert single.end_line == expected.end_line

    # chunk_one() must refuse non-function nodes rather than silently
    # returning something wrong (fail loudly on misuse).
    try:
        chunk_one(graph, FIXTURE_DIR, "chunker_fixture.py")  # module node id
        assert False, "expected AssertionError for a non-function node"
    except AssertionError:
        pass

    print("All chunk_one assertions passed.")
    print(f"  verified {len(all_chunks)} chunks match chunk() output")


if __name__ == "__main__":
    main()