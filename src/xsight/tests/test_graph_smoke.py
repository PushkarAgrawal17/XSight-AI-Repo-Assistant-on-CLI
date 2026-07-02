"""
Smoke test: build the repository graph from real parsed XSight source.

Not a correctness test - verifies build() runs without errors on real
IR and reports plausible counts to eyeball.
"""

import sys
from pathlib import Path

from xsight.graph.builder import build
from xsight.parser.core import parse
from xsight.scanner.core import scan


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m xsight.tests.test_graph_smoke <repo_path>")
        sys.exit(1)

    repo_path = Path(sys.argv[1]).expanduser().resolve()
    result = scan(repo_path)
    python_files = [f for f in result.snapshot.files if f.language == "python"]

    modules = []
    for scanned_file in python_files:
        absolute_path = repo_path / scanned_file.relative_path
        modules.append(parse(absolute_path, scanned_file.relative_path))

    graph = build(modules)

    kinds = {}
    for _, data in graph.nodes(data=True):
        kinds[data["kind"]] = kinds.get(data["kind"], 0) + 1

    edge_types = {}
    for _, _, data in graph.edges(data=True):
        edge_types[data["type"]] = edge_types.get(data["type"], 0) + 1

    print(f"Parsed {len(modules)} modules from {repo_path}\n")
    print("--- Nodes ---")
    for kind, count in sorted(kinds.items()):
        print(f"  {kind}: {count}")
    print(f"  total: {graph.number_of_nodes()}")

    print("\n--- Edges ---")
    for edge_type, count in sorted(edge_types.items()):
        print(f"  {edge_type}: {count}")
    print(f"  total: {graph.number_of_edges()}")


if __name__ == "__main__":
    main()