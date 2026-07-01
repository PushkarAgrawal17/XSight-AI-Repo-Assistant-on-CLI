"""Synchronizes a RepositorySnapshot with the files table for a given repo."""

import sqlite3
from datetime import datetime, timezone

from xsight.indexer.models import IndexSummary
from xsight.scanner.models import RepositorySnapshot, ScannedFile


def sync(
    repo_id: int,
    snapshot: RepositorySnapshot,
    conn: sqlite3.Connection,
) -> IndexSummary:
    """Synchronize the files table with the given snapshot for repo_id."""
    existing = _load_existing_files(repo_id, conn)
    fresh = {f.relative_path: f for f in snapshot.files}

    added = updated = removed = unchanged = 0

    for relative_path, scanned_file in fresh.items():
        existing_row = existing.get(relative_path)

        if existing_row is None:
            _insert_file(repo_id, scanned_file, conn)
            added += 1
        elif existing_row["content_hash"] != scanned_file.content_hash:
            _update_file(repo_id, scanned_file, conn)
            updated += 1
        else:
            unchanged += 1

    for relative_path in existing:
        if relative_path not in fresh:
            _delete_file(repo_id, relative_path, conn)
            removed += 1

    _touch_last_indexed_at(repo_id, conn)
    conn.commit()

    return IndexSummary(
        added=added,
        updated=updated,
        removed=removed,
        unchanged=unchanged,
        total_files=len(fresh),
    )


def _load_existing_files(
    repo_id: int, conn: sqlite3.Connection
) -> dict[str, sqlite3.Row]:
    rows = conn.execute(
        "SELECT relative_path, content_hash FROM files WHERE repo_id = ?",
        (repo_id,),
    ).fetchall()
    return {row["relative_path"]: row for row in rows}


def _insert_file(
    repo_id: int, scanned_file: ScannedFile, conn: sqlite3.Connection
) -> None:
    conn.execute(
        """
        INSERT INTO files
            (repo_id, relative_path, language, content_hash, size_bytes, last_modified)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            repo_id,
            scanned_file.relative_path,
            scanned_file.language,
            scanned_file.content_hash,
            scanned_file.size_bytes,
            scanned_file.last_modified,
        ),
    )


def _update_file(
    repo_id: int, scanned_file: ScannedFile, conn: sqlite3.Connection
) -> None:
    conn.execute(
        """
        UPDATE files
        SET language = ?, content_hash = ?, size_bytes = ?, last_modified = ?
        WHERE repo_id = ? AND relative_path = ?
        """,
        (
            scanned_file.language,
            scanned_file.content_hash,
            scanned_file.size_bytes,
            scanned_file.last_modified,
            repo_id,
            scanned_file.relative_path,
        ),
    )


def _delete_file(
    repo_id: int, relative_path: str, conn: sqlite3.Connection
) -> None:
    conn.execute(
        "DELETE FROM files WHERE repo_id = ? AND relative_path = ?",
        (repo_id, relative_path),
    )


def _touch_last_indexed_at(repo_id: int, conn: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE repositories SET last_indexed_at = ? WHERE id = ?",
        (now, repo_id),
    )