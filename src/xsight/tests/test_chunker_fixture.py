"""
Deterministic chunker regression test.

Runs the real pipeline (parse -> build -> chunk) against a minimal fixture
file, rather than hand-constructing Chunk objects, so this also exercises
_module_of()'s ownership-resolution invariant end to end.
"""

from pathlib import Path

from xsight.chunker.core import chunk
from xsight.graph.builder import build
from xsight.parser.core import parse

FIXTURE_DIR = Path(__file__).parent
FIXTURE_FILE = "chunker_fixture.py"


def main() -> None:
    module = parse(FIXTURE_DIR / FIXTURE_FILE, FIXTURE_FILE)
    graph = build([module])
    chunks = chunk(graph, FIXTURE_DIR)

    # ---- chunk count ----
    assert len(chunks) == 2, f"expected 2 chunks, got {len(chunks)}"

    by_id = {c.id: c for c in chunks}
    assert set(by_id) == {
        "chunker_fixture.py::greet",
        "chunker_fixture.py::Greeter.greet",
    }, "unexpected chunk ids -- possible class chunk leaked through"

    # ---- module-level function chunk ----
    fn_chunk = by_id["chunker_fixture.py::greet"]
    assert fn_chunk.kind == "function"
    assert fn_chunk.relative_path == "chunker_fixture.py"
    assert fn_chunk.start_line == 1 and fn_chunk.end_line == 2

    expected_fn_prefix = "Function: greet\nModule: chunker_fixture.py"
    assert fn_chunk.content.startswith(expected_fn_prefix), (
        f"unexpected prefix:\n{fn_chunk.content}"
    )

    expected_fn_source = 'def greet(name: str) -> str:\n    return f"Hello, {name}!"'
    assert fn_chunk.content == f"{expected_fn_prefix}\n{expected_fn_source}", (
        f"function chunk content mismatch:\n{fn_chunk.content}"
    )

    # ---- method chunk ----
    method_chunk = by_id["chunker_fixture.py::Greeter.greet"]
    assert method_chunk.kind == "function"
    assert method_chunk.relative_path == "chunker_fixture.py"
    assert method_chunk.start_line == 6 and method_chunk.end_line == 7

    expected_method_prefix = "Method: Greeter.greet\nModule: chunker_fixture.py"
    assert method_chunk.content.startswith(expected_method_prefix), (
        f"unexpected prefix:\n{method_chunk.content}"
    )

    expected_method_source = '    def greet(self, name: str) -> str:\n        return f"Hi, {name}!"'
    assert method_chunk.content == f"{expected_method_prefix}\n{expected_method_source}", (
        f"method chunk content mismatch:\n{method_chunk.content}"
    )

    # ---- no duplication / no class chunk ----
    class_chunk_ids = [c.id for c in chunks if c.kind == "class"]
    assert class_chunk_ids == [], f"class chunks should not exist, found: {class_chunk_ids}"

    # the method's source text should not also appear inside the function chunk
    # (sanity check against accidental content bleed across chunks)
    assert expected_method_source not in fn_chunk.content

    print("All assertions passed.")
    print(f"  chunks: {len(chunks)}")
    for c in chunks:
        print(f"  - {c.id} ({c.kind}), lines {c.start_line}-{c.end_line}")


if __name__ == "__main__":
    main()