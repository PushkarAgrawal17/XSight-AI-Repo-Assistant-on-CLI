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

def get_repository(path: Path, conn: sqlite3.Connection) -> int | None:
    resolved_path = str(path.expanduser().resolve())

    row = conn.execute(
        "SELECT id FROM repositories WHERE path = ?",
        (resolved_path,),
    ).fetchone()

    return row["id"] if row is not None else None

def get_file_hashes(repo_id: int, conn: sqlite3.Connection) -> dict[str, str]:
    """Read-only: relative_path -> content_hash for all files currently
    persisted for repo_id. Used by callers that need to detect drift
    against a fresh scan without performing a sync."""
    rows = conn.execute(
        "SELECT relative_path, content_hash FROM files WHERE repo_id = ?",
        (repo_id,),
    ).fetchall()
    return {row["relative_path"]: row["content_hash"] for row in rows}

def get_cached_modules(repo_id: int, conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute(
        "SELECT relative_path, data FROM parsed_modules WHERE repo_id = ?",
        (repo_id,),
    ).fetchall()
    return {row["relative_path"]: row["data"] for row in rows}


def save_parsed_module(
    repo_id: int, relative_path: str, content_hash: str, data: str, conn: sqlite3.Connection
) -> None:
    conn.execute(
        """
        INSERT INTO parsed_modules (repo_id, relative_path, content_hash, data)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (repo_id, relative_path)
        DO UPDATE SET content_hash = excluded.content_hash, data = excluded.data
        """,
        (repo_id, relative_path, content_hash, data),
    )


def delete_parsed_modules(repo_id: int, relative_paths: list[str], conn: sqlite3.Connection) -> None:
    if not relative_paths:
        return
    conn.executemany(
        "DELETE FROM parsed_modules WHERE repo_id = ? AND relative_path = ?",
        [(repo_id, path) for path in relative_paths],
    )


def list_repositories(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Read-only: every indexed repository, ordered by id. Used by commands
    that need the repository catalog rather than a single repository."""
    return conn.execute(
        "SELECT id, name, path, last_indexed_at FROM repositories ORDER BY id"
    ).fetchall()


def delete_repository(repo_id: int, conn: sqlite3.Connection) -> None:
    """Delete all persisted data for a repository: parsed modules, files,
    and the repository row itself, in FK-safe child-before-parent order.
    Caller commits."""
    conn.execute("DELETE FROM parsed_modules WHERE repo_id = ?", (repo_id,))
    conn.execute("DELETE FROM files WHERE repo_id = ?", (repo_id,))
    conn.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))


def get_repository_by_id(repo_id: int, conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Read-only: full repository row by id. Used by callers that already
    have a repo_id and need its display metadata (name/path/timestamps)."""
    return conn.execute(
        "SELECT id, name, path, created_at, last_indexed_at FROM repositories WHERE id = ?",
        (repo_id,),
    ).fetchone()


def clear_parsed_modules(repo_id: int, conn: sqlite3.Connection) -> int:
    """Delete all cached parsed modules for a repository, leaving files
    and repositories rows untouched. Returns the number of rows deleted.
    Caller commits."""
    cursor = conn.execute("DELETE FROM parsed_modules WHERE repo_id = ?", (repo_id,))
    return cursor.rowcount