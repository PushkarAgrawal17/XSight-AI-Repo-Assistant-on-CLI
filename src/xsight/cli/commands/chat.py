"""`xsight chat` command."""

from pathlib import Path
from typing import Callable

import typer
from google.genai import errors as genai_errors
from rich.console import Console

from xsight.chat.core import NoResultsError, answer_question
from xsight.chat.models import ChatTurn
from xsight.cli.commands._pipeline import run_pipeline
from xsight.config.settings import settings
from xsight.database.connection import get_connection
from xsight.database.repositories import get_file_hashes, get_repository
from xsight.embeddings.provider import OllamaEmbeddingProvider
from xsight.graph.builder import build
from xsight.llm.provider import GeminiLLMProvider
from xsight.parser.core import parse
from xsight.scanner.core import scan
from xsight.vectorstore.provider import QdrantVectorStoreProvider

console = Console()

HISTORY_WINDOW = 4


def _has_changed(scan_result, repo_id: int, conn) -> bool:
    """Compare a fresh scan against persisted file hashes. Read-only."""
    existing = get_file_hashes(repo_id, conn)
    fresh = {f.relative_path: f.content_hash for f in scan_result.snapshot.files}
    return existing != fresh


def _load_graph(resolved_path, scan_result):
    python_files = [f for f in scan_result.snapshot.files if f.language == "python"]
    modules = [
        parse(resolved_path / f.relative_path, f.relative_path) for f in python_files
    ]
    return build(modules)


def run(query: str | None = typer.Argument(None), path: Path = typer.Argument(Path("."))) -> None:
    resolved_path = path.expanduser().resolve()

    conn = get_connection()
    repo_id = get_repository(resolved_path, conn)

    if repo_id is None:
        conn.close()
        console.print("[red]Repository hasn't been indexed. Run `xsight init` first.[/red]")
        raise typer.Exit(1)

    scan_result = scan(resolved_path)
    changed = _has_changed(scan_result, repo_id, conn)
    conn.close()

    if changed:
        console.print("[yellow]Repository has changed since the last index.[/yellow]")
        if typer.confirm("Run `xsight update` now?", default=True):
            run_pipeline(resolved_path, lambda p, c: get_repository(p, c))
            scan_result = scan(resolved_path)  # fresh snapshot post-update

    graph = _load_graph(resolved_path, scan_result)

    embedding_provider = OllamaEmbeddingProvider(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
    vectorstore_provider = QdrantVectorStoreProvider(
        collection_name=settings.qdrant_collection,
        url=settings.qdrant_url,
    )

    if settings.gemini_api_key is None:
        console.print("[red]Error:[/red] GEMINI_API_KEY is not configured.")
        raise typer.Exit(code=1)

    llm_provider = GeminiLLMProvider(
        model=settings.gemini_model,
        api_key=settings.gemini_api_key,
    )

    history: list[ChatTurn] = []

    def cmd_help() -> None:
        console.print(
            "[bold]Available commands:[/bold]\n"
            "  help     Show this help message\n"
            "  history  Show the current conversation history\n"
            "  clear    Clear conversation history\n"
            "  stats    Show session information\n"
            "  exit     Leave the chat session\n"
            "  quit     Leave the chat session"
        )

    def _preview(text: str) -> str:
        return text if len(text) <= 200 else text[:200] + "..."

    def cmd_history() -> None:
        if not history:
            console.print("[dim](no conversation history yet)[/dim]")
            return
        for i, turn in enumerate(history, start=1):
            console.print(f"[bold]{i}. User:[/bold] {turn.question}")
            console.print(f"   [bold]Assistant:[/bold] {_preview(turn.answer)}")

    def cmd_clear() -> None:
        history.clear()
        console.print("[dim]Conversation history cleared.[/dim]")

    def cmd_stats() -> None:
        console.print(
            f"[bold]Repository:[/bold] {resolved_path}\n"
            f"[bold]Repo ID:[/bold] {repo_id}\n"
            f"[bold]Conversation turns:[/bold] {len(history)}\n"
            f"[bold]History window:[/bold] {HISTORY_WINDOW}\n"
            f"[bold]Graph nodes:[/bold] {graph.number_of_nodes()}\n"
            f"[bold]Graph edges:[/bold] {graph.number_of_edges()}"
        )

    commands: dict[str, Callable[[], None]] = {
        "help": cmd_help,
        "history": cmd_history,
        "clear": cmd_clear,
        "stats": cmd_stats,
    }

    def ask(q: str) -> None:
        try:
            answer = answer_question(
                query=q,
                repo_id=repo_id,
                graph=graph,
                repo_path=resolved_path,
                embedding_provider=embedding_provider,
                vectorstore_provider=vectorstore_provider,
                llm_provider=llm_provider,
                history=history,
            )
        except NoResultsError:
            console.print(
                "[yellow]No indexed code was found for this repository. "
                "Run `xsight init` again.[/yellow]"
            )
            return
        except genai_errors.APIError as e:
            console.print(
                f"[red]Gemini API error ({e.code}): {e.message}[/red]\n"
                "[red]Check your GEMINI_API_KEY and network connection.[/red]"
            )
            return
        console.print(answer)
        history.append(ChatTurn(question=q, answer=answer))
        del history[:-HISTORY_WINDOW]

    if query is not None:
        ask(query)
        return

    console.print("[dim]XSight chat -- type 'exit' or 'quit' to leave.[/dim]")
    while True:
        try:
            user_input = console.input("[bold]> [/bold]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        command = commands.get(user_input.lower())
        if command is not None:
            command()
            console.print()
            continue

        ask(user_input)
        console.print()