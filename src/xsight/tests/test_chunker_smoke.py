"""
Smoke test: run scan -> parse -> build -> chunk against a real repository.

Not a correctness test against known values -- validates structural
invariants and prints statistics to eyeball.
"""

import sys
from pathlib import Path

from xsight.chunker.core import chunk
from xsight.graph.builder import build
from xsight.parser.core import parse
from xsight.scanner.core import scan


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m xsight.tests.test_chunker_smoke <repo_path>")
        sys.exit(1)

    repo_path = Path(sys.argv[1]).expanduser().resolve()
    result = scan(repo_path)
    python_files = [f for f in result.snapshot.files if f.language == "python"]

    modules = [
        parse(repo_path / f.relative_path, f.relative_path) for f in python_files
    ]
    graph = build(modules)
    chunks = chunk(graph, repo_path)

    function_nodes = [n for n, d in graph.nodes(data=True) if d["kind"] == "function"]

    # ---- invariants ----
    assert len(chunks) == len(function_nodes), (
        f"chunk count ({len(chunks)}) != function node count ({len(function_nodes)})"
    )

    chunk_ids = [c.id for c in chunks]
    assert len(chunk_ids) == len(set(chunk_ids)), "duplicate chunk ids found"

    for c in chunks:
        assert c.id in graph.nodes, f"chunk id {c.id} not found in graph"
        assert c.kind == "function", f"unexpected chunk kind: {c.kind} ({c.id})"
        assert c.start_line <= c.end_line, f"invalid line range for {c.id}"
        assert c.content.strip() != "", f"empty content for {c.id}"
        assert "\n" in c.content, f"chunk missing prefix/body separation: {c.id}"

    # ---- statistics ----
    lengths = [c.end_line - c.start_line + 1 for c in chunks]
    shortest = min(chunks, key=lambda c: c.end_line - c.start_line)
    longest = max(chunks, key=lambda c: c.end_line - c.start_line)

    print("All invariants passed.\n")
    print(f"Modules parsed:     {len(modules)}")
    print(f"Function nodes:     {len(function_nodes)}")
    print(f"Chunks generated:   {len(chunks)}")
    print(f"Average chunk length: {sum(lengths) / len(lengths):.1f} lines")
    print(f"Shortest chunk: {shortest.id} ({shortest.end_line - shortest.start_line + 1} lines)")
    print(f"Longest chunk:  {longest.id} ({longest.end_line - longest.start_line + 1} lines)")


if __name__ == "__main__":
    main()