"""SQLite schema definitions for XSight."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_indexed_at TEXT
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL,
    relative_path TEXT NOT NULL,
    language TEXT,
    content_hash TEXT,
    size_bytes INTEGER,
    last_modified TEXT,
    FOREIGN KEY (repo_id) REFERENCES repositories(id),
    UNIQUE (repo_id, relative_path)
);

CREATE TABLE IF NOT EXISTS parsed_modules (
    repo_id INTEGER NOT NULL,
    relative_path TEXT NOT NULL,
    content_hash TEXT,
    data TEXT NOT NULL,
    FOREIGN KEY (repo_id) REFERENCES repositories(id),
    UNIQUE (repo_id, relative_path)
);
"""
