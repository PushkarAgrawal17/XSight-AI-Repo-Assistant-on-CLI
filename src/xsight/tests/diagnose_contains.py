import sys
from pathlib import Path

from xsight.graph.builder import build
from xsight.parser.core import parse
from xsight.scanner.core import scan


def main() -> None:
    repo_path = Path(sys.argv[1]).expanduser().resolve()
    result = scan(repo_path)
    python_files = [f for f in result.snapshot.files if f.language == "python"]

    modules = []
    for scanned_file in python_files:
        absolute_path = repo_path / scanned_file.relative_path
        modules.append(parse(absolute_path, scanned_file.relative_path))

    expected_contains = sum(len(m.classes) + len(m.functions) for m in modules)
    print(f"Expected contains edges: {expected_contains}")

    graph = build(modules)
    contains_edges = [(u, v) for u, v, data in graph.edges(data=True) if data["type"] == "contains"]
    print(f"Actual contains edges: {len(contains_edges)}\n")

    # per-module breakdown
    for module in modules:
        expected = len(module.classes) + len(module.functions)
        outgoing_from_module = sum(1 for u, v in contains_edges if u == module.relative_path)
        outgoing_from_classes = sum(
            1 for u, v in contains_edges
            for c in module.classes if u == c.id
        )
        actual = outgoing_from_module + outgoing_from_classes
        if actual != expected:
            print(f"MISMATCH in {module.relative_path}: expected {expected}, got {actual}")
            print(f"  classes: {[c.id for c in module.classes]}")
            print(f"  functions: {[(f.id, f.parent_id) for f in module.functions]}")

    # invariant check: every node has exactly one incoming contains edge
    print("\n--- Invariant check ---")
    incoming_counts = {}
    for u, v in contains_edges:
        incoming_counts[v] = incoming_counts.get(v, 0) + 1

    for node, count in incoming_counts.items():
        if count != 1:
            incoming = [(u, v, k) for u, v, k in graph.in_edges(node, keys=True) if graph[u][v][k]["type"] == "contains"]
            print(f"VIOLATION: {node} has {count} incoming contains edges: {incoming}")


if __name__ == "__main__":
    main()