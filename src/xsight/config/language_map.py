"""Language classification for the repository scanner.

This module is responsible only for mapping a file to a language label.
It has no knowledge of Tree-sitter parsing support, ignore rules, or
scanner logic — a file can be classified here even if XSight cannot yet
parse that language.
"""

LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py", ".pyi"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp"],
    "go": [".go"],
    "rust": [".rs"],
    "csharp": [".cs"],
    "php": [".php"],
    "ruby": [".rb"],
    "kotlin": [".kt", ".kts"],
    "swift": [".swift"],
    "dart": [".dart"],
    "html": [".html", ".htm"],
    "css": [".css"],
    "scss": [".scss"],
    "sql": [".sql"],
    "json": [".json"],
    "yaml": [".yaml", ".yml"],
    "toml": [".toml"],
    "xml": [".xml"],
    "markdown": [".md", ".markdown"],
    "shell": [".sh", ".bash", ".zsh"],
}

SPECIAL_FILENAMES: dict[str, str] = {
    "Dockerfile": "dockerfile",
    "Makefile": "makefile",
    "CMakeLists.txt": "cmake",
}

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ext: lang for lang, exts in LANGUAGE_EXTENSIONS.items() for ext in exts
}


def detect_language(filename: str) -> str | None:
    """Classify a file by language, or return None if unrecognized.

    Checks special filenames first (exact match), then falls back to
    a case-insensitive extension lookup.
    """
    if filename in SPECIAL_FILENAMES:
        return SPECIAL_FILENAMES[filename]

    suffix_index = filename.rfind(".")
    if suffix_index == -1:
        return None

    extension = filename[suffix_index:].lower()
    return EXTENSION_TO_LANGUAGE.get(extension)