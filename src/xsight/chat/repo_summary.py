"""Deterministic repository summary built from scanner + graph metadata.

No LLM calls, no embeddings, no persistence -- built fresh each chat
invocation from data XSight already computed (RepositorySnapshot, graph).
"""

from pathlib import Path

import networkx as nx

from xsight.scanner.models import RepositorySnapshot

ENTRYPOINT_CANDIDATES = {"main.py", "cli.py", "__main__.py", "app.py"}


def build_repo_summary(repo_path: Path, snapshot: RepositorySnapshot, graph: nx.MultiDiGraph) -> str:
    """Build a short factual repository overview. Omits any section with
    nothing to report rather than guessing."""
    lines = [f"Repository: {repo_path.name}"]

    languages = sorted({f.language for f in snapshot.files if f.language})
    if languages:
        lines.append(f"Languages: {', '.join(languages)}")

    python_files = [f for f in snapshot.files if f.language == "python"]
    if python_files:
        lines.append(f"Python modules: {len(python_files)}")

    top_level = sorted({
        f.relative_path.split("/")[0]
        for f in python_files
        if "/" in f.relative_path
    })
    if top_level:
        lines.append(f"Top-level packages/directories: {', '.join(top_level)}")

    class_count = sum(1 for _, d in graph.nodes(data=True) if d["kind"] == "class")
    function_count = sum(1 for _, d in graph.nodes(data=True) if d["kind"] == "function")
    if class_count or function_count:
        lines.append(f"Classes: {class_count}, Functions/Methods: {function_count}")

    entrypoints = sorted({
        f.relative_path
        for f in python_files
        if Path(f.relative_path).name in ENTRYPOINT_CANDIDATES
    })
    if entrypoints:
        lines.append(f"Likely entrypoints: {', '.join(entrypoints)}")

    return "\n".join(lines)