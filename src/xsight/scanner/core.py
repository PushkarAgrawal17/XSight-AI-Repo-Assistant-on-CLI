"""Filesystem scanning logic.

Walks a repository, applies ignore rules, and produces a RepositorySnapshot
plus a ScanSummary. Has no knowledge of SQLite or any persistence layer.
"""

import fnmatch
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from xsight.config.ignore import (
    BINARY_EXTENSIONS,
    IGNORED_DIRECTORIES,
    IGNORED_FILE_PATTERNS,
)
from xsight.config.language_map import detect_language
from xsight.scanner.models import (
    RepositorySnapshot,
    ScannedFile,
    ScanResult,
    ScanSummary,
)

MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB
IGNORE_FILE_NAME = ".xsightignore"
HASH_CHUNK_SIZE = 65536


def scan(repo_path: Path) -> ScanResult:
    """Scan a repository and return its snapshot plus scan metrics."""
    resolved_path = repo_path.expanduser().resolve()
    ignored_dirs, ignored_patterns = _load_ignore_rules(resolved_path)

    files: list[ScannedFile] = []
    ignored_files = 0
    ignored_directories = 0
    skipped_binary_files = 0
    skipped_large_files = 0
    errors = 0

    for dirpath, dirnames, filenames in os.walk(resolved_path):
        dirnames.sort()
        pruned = [d for d in dirnames if d in ignored_dirs]
        ignored_directories += len(pruned)
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]

        for filename in sorted(filenames):
            file_path = Path(dirpath) / filename

            if _matches_any_pattern(filename, ignored_patterns):
                ignored_files += 1
                continue

            if file_path.suffix.lower() in BINARY_EXTENSIONS:
                skipped_binary_files += 1
                continue

            try:
                file_stat = file_path.stat()
            except OSError:
                errors += 1
                continue

            if file_stat.st_size > MAX_FILE_SIZE_BYTES:
                skipped_large_files += 1
                continue

            try:
                scanned_file = _build_scanned_file(
                    file_path, resolved_path, file_stat
                )
            except OSError:
                errors += 1
                continue

            files.append(scanned_file)

    snapshot = RepositorySnapshot(
        repo_path=resolved_path,
        scanned_at=_utc_now_iso(),
        files=files,
    )
    summary = ScanSummary(
        ignored_files=ignored_files,
        ignored_directories=ignored_directories,
        skipped_binary_files=skipped_binary_files,
        skipped_large_files=skipped_large_files,
        errors=errors,
    )
    return ScanResult(snapshot=snapshot, summary=summary)


def _build_scanned_file(
    file_path: Path, repo_root: Path, file_stat: os.stat_result
) -> ScannedFile:
    """Build a ScannedFile for a file that passed all ignore checks."""
    content_hash = _hash_file(file_path)
    last_modified = datetime.fromtimestamp(
        file_stat.st_mtime, tz=timezone.utc
    ).isoformat()

    return ScannedFile(
        relative_path=file_path.relative_to(repo_root).as_posix(),
        language=detect_language(file_path.name),
        content_hash=content_hash,
        size_bytes=file_stat.st_size,
        last_modified=last_modified,
    )


def _hash_file(file_path: Path) -> str:
    """Compute the SHA-256 hash of a file's contents, read in chunks."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(HASH_CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _matches_any_pattern(filename: str, patterns: set[str]) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)


def _load_ignore_rules(repo_root: Path) -> tuple[set[str], set[str]]:
    """Merge default ignore rules with .xsightignore, if present.

    Returns (ignored_directories, ignored_file_patterns).
    """
    ignored_dirs = set(IGNORED_DIRECTORIES)
    ignored_patterns = set(IGNORED_FILE_PATTERNS)

    ignore_file = repo_root / IGNORE_FILE_NAME
    if not ignore_file.is_file():
        return ignored_dirs, ignored_patterns

    try:
        content = ignore_file.read_text(encoding="utf-8")
    except OSError:
        return ignored_dirs, ignored_patterns

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("/"):
            ignored_dirs.add(line.rstrip("/"))
        else:
            ignored_patterns.add(line)

    return ignored_dirs, ignored_patterns


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()