"""`xsight config` command — read-only display of the effective runtime
configuration. Never writes, never contacts Qdrant/LLM/database, never
scans a repository. Reads directly from the existing `settings` singleton
and `config/ignore.py` static data.

Field values are rendered dynamically via settings.model_dump() so any
newly added Settings field automatically appears without modifying this
file's render logic. Grouping fields into named sections still requires
mapping a field NAME to a section (Pydantic has no built-in grouping
metadata) — fields not yet mapped land under "Other" rather than being
silently dropped, so nothing new is ever hidden.

Every value is routed through _display(), which masks any field whose
name contains key/token/secret/password — this applies uniformly to
dynamically discovered fields too, not just fields explicitly listed here.
"""

from rich.console import Console
from rich.panel import Panel

from xsight.config.ignore import BINARY_EXTENSIONS, IGNORED_DIRECTORIES, IGNORED_FILE_PATTERNS
from xsight.config.settings import settings

console = Console()

_SENSITIVE_MARKERS = ("key", "token", "secret", "password")

# field name -> section. Fields not listed here fall into "Other".
_SECTIONS: dict[str, str] = {
    "db_path": "Paths",
    "qdrant_url": "Qdrant",
    "qdrant_collection": "Qdrant",
    "embedding_model": "Embeddings",
    "ollama_base_url": "Embeddings",
    "gemini_model": "LLM",
    "gemini_api_key": "LLM",
}

_SECTION_ORDER = ["Paths", "Qdrant", "Embeddings", "LLM", "Other"]

_LABELS: dict[str, str] = {
    "db_path": "Database",
    "qdrant_url": "URL",
    "qdrant_collection": "Collection",
    "embedding_model": "Model",
    "ollama_base_url": "Ollama URL",
    "gemini_model": "Chat Model",
    "gemini_api_key": "API Key",
}


def _mask(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def _display(field_name: str, value) -> str:
    if value is None:
        return "[dim]not set[/dim]"
    if any(marker in field_name.lower() for marker in _SENSITIVE_MARKERS):
        return _mask(str(value))
    return str(value)


def run() -> None:
    console.rule("[bold cyan]XSight Configuration[/bold cyan]")
    console.print("[bold cyan]Current Runtime Configuration[/bold cyan]")
    console.print()

    fields = settings.model_dump()

    grouped: dict[str, list[str]] = {section: [] for section in _SECTION_ORDER}
    for field_name, value in fields.items():
        section = _SECTIONS.get(field_name, "Other")
        label = _LABELS.get(field_name, field_name)
        grouped[section].append(f"[bold]{label}[/bold] : {_display(field_name, value)}")

    for section in _SECTION_ORDER:
        lines = grouped[section]
        if not lines:
            continue
        console.print(
            Panel(
                "\n".join(lines),
                title=section,
                title_align="left",
                border_style="cyan",
            )
        )
        console.print()

    console.print(
        Panel(
            f"[bold]Ignored directories[/bold]      : {len(IGNORED_DIRECTORIES)}\n"
            f"[bold]Ignored file patterns[/bold]    : {len(IGNORED_FILE_PATTERNS)}\n"
            f"[bold]Ignored binary extensions[/bold] : {len(BINARY_EXTENSIONS)}",
            title="Scanner",
            title_align="left",
            border_style="cyan",
        )
    )
    console.print()