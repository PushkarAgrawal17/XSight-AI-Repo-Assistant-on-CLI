"""Canonical fixture for indexer tests: hand-built scan snapshots
covering the 5 sync scenarios (fresh, no-op, modified, added, removed)."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from xsight.database.models import SCHEMA
from xsight.scanner.models import RepositorySnapshot, ScannedFile


def make_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def make_file(relative_path: str, content_hash: str) -> ScannedFile:
    return ScannedFile(
        relative_path=relative_path,
        language="python",
        content_hash=content_hash,
        size_bytes=100,
        last_modified=datetime.now(timezone.utc).isoformat(),
    )


def make_snapshot(repo_path: Path, files: list[ScannedFile]) -> RepositorySnapshot:
    return RepositorySnapshot(
        repo_path=repo_path,
        scanned_at=datetime.now(timezone.utc).isoformat(),
        files=files,
    )