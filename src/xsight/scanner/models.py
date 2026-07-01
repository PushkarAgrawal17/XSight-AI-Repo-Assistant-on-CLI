"""Data contracts for the scanner package.

These dataclasses represent repository state (RepositorySnapshot) and
scan execution metrics (ScanSummary) as separate concerns.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScannedFile:
    relative_path: str
    language: str | None
    content_hash: str
    size_bytes: int
    last_modified: str  # ISO 8601


@dataclass
class RepositorySnapshot:
    repo_path: Path
    scanned_at: str  # ISO 8601
    files: list[ScannedFile]


@dataclass
class ScanSummary:
    ignored_files: int
    ignored_directories: int
    skipped_binary_files: int
    skipped_large_files: int
    errors: int


@dataclass
class ScanResult:
    snapshot: RepositorySnapshot
    summary: ScanSummary