"""Default ignore rules for the repository scanner.

These are static defaults. User-specific overrides are supplied via a
`.xsightignore` file at the repository root and merged in by the scanner
at scan time — this module has no knowledge of that merging.
"""

IGNORED_DIRECTORIES: set[str] = {
    ".git", ".github", ".venv", "venv", "env",
    "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".idea", ".vscode",
    "dist", "build", "target", "coverage", ".coverage",
    ".tox", ".cache",
}

IGNORED_FILE_PATTERNS: set[str] = {
    "*.pyc", "*.pyo", "*.class", "*.o", "*.obj",
    "*.so", "*.dll", "*.exe", "*.bin", "*.log",
    "*.lock", "*.min.js", "*.min.css", "*.map",
}

BINARY_EXTENSIONS: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".mp3", ".wav", ".mp4", ".mov",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".pdf", ".docx", ".xlsx",
}