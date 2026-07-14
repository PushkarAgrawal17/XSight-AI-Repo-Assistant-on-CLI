"""Fixture test for xsight.database.repositories.get_file_hashes."""

import sqlite3
from pathlib import Path

from xsight.database.models import SCHEMA
from xsight.database.repositories import get_file_hashes, get_or_create_repository


def main() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    repo_id = get_or_create_repository(Path(__file__), conn)  # path value irrelevant for this test's purpose

    # Empty repo -> empty dict
    assert get_file_hashes(repo_id, conn) == {}, "expected empty dict for repo with no files"

    conn.execute(
        "INSERT INTO files (repo_id, relative_path, language, content_hash, size_bytes, last_modified) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (repo_id, "a.py", "python", "hash_a", 10, "2024-01-01T00:00:00+00:00"),
    )
    conn.execute(
        "INSERT INTO files (repo_id, relative_path, language, content_hash, size_bytes, last_modified) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (repo_id, "b.py", "python", "hash_b", 20, "2024-01-01T00:00:00+00:00"),
    )
    conn.commit()

    result = get_file_hashes(repo_id, conn)
    assert result == {"a.py": "hash_a", "b.py": "hash_b"}, f"unexpected result: {result}"

    # Different repo_id must not see these files
    other_repo_id = get_or_create_repository(
        Path(__file__).with_name("other_repo"),
        conn,
    )
    assert get_file_hashes(other_repo_id, conn) == {}, "hashes leaked across repo_id"

    print("test_repositories_fixture: all assertions passed")


if __name__ == "__main__":
    main()