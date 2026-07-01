"""Persistence helpers for the repositories table.

These are simple CRUD operations, not business logic. Diffing and
synchronization decisions belong in the indexer, not here.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def get_or_create_repository(path: Path, conn: sqlite3.Connection) -> int:
    """Return the repo_id for a repository, creating it if it doesn't exist."""
    resolved_path = str(path)

    row = conn.execute(
        "SELECT id FROM repositories WHERE path = ?", (resolved_path,)
    ).fetchone()
    if row is not None:
        return row["id"]

    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO repositories (path, name, created_at) VALUES (?, ?, ?)",
        (resolved_path, path.name, now),
    )
    conn.commit()
    return cursor.lastrowid