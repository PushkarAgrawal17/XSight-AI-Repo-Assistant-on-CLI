"""Deterministic test for build_repo_summary()."""

from pathlib import Path

import networkx as nx

from xsight.chat.repo_summary import build_repo_summary
from xsight.scanner.models import RepositorySnapshot, ScannedFile


def _file(path, language="python"):
    return ScannedFile(
        relative_path=path, language=language, content_hash="x",
        size_bytes=1, last_modified="2026-01-01T00:00:00",
    )


def main() -> None:
    snapshot = RepositorySnapshot(
        repo_path=Path("/repo"),
        scanned_at="2026-01-01T00:00:00",
        files=[
            _file("src/xsight/cli/main.py"),
            _file("src/xsight/scanner/core.py"),
            _file("README.md", language="markdown"),
        ],
    )

    graph = nx.MultiDiGraph()
    graph.add_node("a", kind="class", name="A", start_line=1, end_line=5)
    graph.add_node("b", kind="function", name="b", start_line=1, end_line=2)

    summary = build_repo_summary(Path("/repo/xsight"), snapshot, graph)

    assert "Repository: xsight" in summary
    assert "Languages: markdown, python" in summary
    assert "Python modules: 2" in summary
    assert "Top-level packages/directories: src" in summary
    assert "Classes: 1, Functions/Methods: 1" in summary
    assert "Likely entrypoints: src/xsight/cli/main.py" in summary

    # ---- empty snapshot: no fabricated sections ----
    empty_snapshot = RepositorySnapshot(repo_path=Path("/x"), scanned_at="t", files=[])
    empty_graph = nx.MultiDiGraph()
    empty_summary = build_repo_summary(Path("/x"), empty_snapshot, empty_graph)
    assert empty_summary == "Repository: x"

    print("All repo_summary assertions passed.")


if __name__ == "__main__":
    main()