"""SQLite connection management for XSight's global metadata DB."""

import sqlite3
from pathlib import Path

from xsight.database.models import SCHEMA

DEFAULT_DB_PATH = Path.home() / ".xsight" / "xsight.db"


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return a SQLite connection, creating the DB and schema if needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA)
    return conn
