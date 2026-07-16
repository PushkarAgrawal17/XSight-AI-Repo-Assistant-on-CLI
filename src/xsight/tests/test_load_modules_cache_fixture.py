"""Fixture test: load_modules() cache-hit/miss/delete behavior and graph equivalence."""

import sqlite3
from pathlib import Path

from xsight.cli.commands._pipeline import load_modules
from xsight.database.models import SCHEMA
from xsight.graph.builder import build
from xsight.indexer.models import IndexSummary
from xsight.parser.core import parse
from xsight.scanner.models import ScannedFile


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO repositories (id, path, name, created_at) VALUES (1, '/tmp/repo', 'repo', '2026-01-01')"
    )
    conn.commit()
    return conn


def main() -> None:
    fixture_dir = Path(__file__).parent
    fixture_file = fixture_dir / "parser_fixture.py"
    assert fixture_file.exists(), f"missing canonical fixture: {fixture_file}"

    files = [
        ScannedFile(relative_path="parser_fixture.py", language="python",
                    content_hash="hash-a", size_bytes=fixture_file.stat().st_size,
                    last_modified="2026-01-01"),
    ]
    conn = _conn()

    # First run: everything is "added" -> full parse, cache populated.
    first_summary = IndexSummary(added=len(files), updated=0, removed=0, unchanged=0,
                                  total_files=len(files),
                                  added_files=[f.relative_path for f in files],
                                  updated_files=[], removed_files=[])
    fresh_modules = load_modules(fixture_dir, 1, files, first_summary, conn)
    conn.commit()
    assert len(fresh_modules) == len(files)

    # Second run: nothing changed -> should load from cache, not reparse.
    second_summary = IndexSummary(added=0, updated=0, removed=0, unchanged=len(files),
                                   total_files=len(files),
                                   added_files=[], updated_files=[], removed_files=[])
    cached_modules = load_modules(fixture_dir, 1, files, second_summary, conn)

    # Graph-equivalence invariant: cached-mixed assembly must match a fully-fresh parse.
    truly_fresh = [parse(fixture_dir / f.relative_path, f.relative_path) for f in files]
    g_cached = build(cached_modules)
    g_fresh = build(truly_fresh)
    assert set(g_cached.nodes) == set(g_fresh.nodes), "node set mismatch after cache reuse"
    assert set(g_cached.edges) == set(g_fresh.edges), "edge set mismatch after cache reuse"

    # Removal: dropping one file must remove its cache row.
    # Removal: dropping the only file must remove its cache row.
    removed_path = files[0].relative_path
    removal_summary = IndexSummary(added=0, updated=0, removed=1, unchanged=0,
                                    total_files=0,
                                    added_files=[], updated_files=[], removed_files=[removed_path])
    remaining_modules = load_modules(fixture_dir, 1, [], removal_summary, conn)
    conn.commit()
    assert removed_path not in {m.relative_path for m in remaining_modules}
    row = conn.execute(
        "SELECT 1 FROM parsed_modules WHERE repo_id = 1 AND relative_path = ?", (removed_path,)
    ).fetchone()
    assert row is None, "cache row for removed file was not deleted"

    conn.close()
    print("OK: load_modules cache hit/miss/delete + graph equivalence")


if __name__ == "__main__":
    main()