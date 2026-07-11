"""Fixture test for indexer.sync() — 5 scenarios, verifying both
aggregate counts and the changed-file path lists they expose."""

from pathlib import Path

from xsight.database.repositories import get_or_create_repository
from xsight.indexer.core import sync
from xsight.tests.indexer_fixture import make_connection, make_file, make_snapshot

REPO_PATH = Path("/fake/repo")


def main() -> None:
    conn = make_connection()
    repo_id = get_or_create_repository(REPO_PATH, conn)

    # 1. Fresh scan — all added
    snapshot = make_snapshot(REPO_PATH, [
        make_file("a.py", "hash_a1"),
        make_file("b.py", "hash_b1"),
    ])
    summary = sync(repo_id, snapshot, conn)
    assert summary.added == 2, f"expected 2 added, got {summary.added}"
    assert summary.updated == 0, f"expected 0 updated, got {summary.updated}"
    assert summary.removed == 0, f"expected 0 removed, got {summary.removed}"
    assert summary.unchanged == 0, f"expected 0 unchanged, got {summary.unchanged}"
    assert set(summary.added_files) == {"a.py", "b.py"}, (
        f"expected added_files {{'a.py', 'b.py'}}, got {summary.added_files}"
    )
    assert summary.updated_files == [], f"expected no updated_files, got {summary.updated_files}"
    assert summary.removed_files == [], f"expected no removed_files, got {summary.removed_files}"

    # 2. No-op re-run — all unchanged
    summary = sync(repo_id, snapshot, conn)
    assert summary.unchanged == 2, f"expected 2 unchanged, got {summary.unchanged}"
    assert summary.added_files == [], f"expected no added_files, got {summary.added_files}"
    assert summary.updated_files == [], f"expected no updated_files, got {summary.updated_files}"
    assert summary.removed_files == [], f"expected no removed_files, got {summary.removed_files}"

    # 3. Single-file modification
    snapshot_modified = make_snapshot(REPO_PATH, [
        make_file("a.py", "hash_a2"),  # changed hash
        make_file("b.py", "hash_b1"),  # unchanged
    ])
    summary = sync(repo_id, snapshot_modified, conn)
    assert summary.updated == 1, f"expected 1 updated, got {summary.updated}"
    assert summary.unchanged == 1, f"expected 1 unchanged, got {summary.unchanged}"
    assert summary.updated_files == ["a.py"], f"expected updated_files ['a.py'], got {summary.updated_files}"
    assert summary.added_files == [], f"expected no added_files, got {summary.added_files}"
    assert summary.removed_files == [], f"expected no removed_files, got {summary.removed_files}"

    # 4. Single-file addition
    snapshot_added = make_snapshot(REPO_PATH, [
        make_file("a.py", "hash_a2"),
        make_file("b.py", "hash_b1"),
        make_file("c.py", "hash_c1"),  # new
    ])
    summary = sync(repo_id, snapshot_added, conn)
    assert summary.added == 1, f"expected 1 added, got {summary.added}"
    assert summary.unchanged == 2, f"expected 2 unchanged, got {summary.unchanged}"
    assert summary.added_files == ["c.py"], f"expected added_files ['c.py'], got {summary.added_files}"
    assert summary.updated_files == [], f"expected no updated_files, got {summary.updated_files}"
    assert summary.removed_files == [], f"expected no removed_files, got {summary.removed_files}"

    # 5. Single-file deletion
    snapshot_removed = make_snapshot(REPO_PATH, [
        make_file("a.py", "hash_a2"),
        make_file("b.py", "hash_b1"),
    ])
    summary = sync(repo_id, snapshot_removed, conn)
    assert summary.removed == 1, f"expected 1 removed, got {summary.removed}"
    assert summary.unchanged == 2, f"expected 2 unchanged, got {summary.unchanged}"
    assert summary.removed_files == ["c.py"], f"expected removed_files ['c.py'], got {summary.removed_files}"
    assert summary.added_files == [], f"expected no added_files, got {summary.added_files}"
    assert summary.updated_files == [], f"expected no updated_files, got {summary.updated_files}"

    conn.close()
    print("All indexer fixture assertions passed.")


if __name__ == "__main__":
    main()