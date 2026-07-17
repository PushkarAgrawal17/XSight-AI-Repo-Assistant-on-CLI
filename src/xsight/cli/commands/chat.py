"""`xsight chat` command."""

from pathlib import Path
from typing import Callable

import typer
from google.genai import errors as genai_errors
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown

from xsight.chat.core import NoResultsError, answer_question
from xsight.chat.models import ChatTurn
from xsight.chat.repo_summary import build_repo_summary
from xsight.cli.commands._pipeline import run_pipeline, load_repo_graph
from xsight.config.settings import settings
from xsight.database.connection import get_connection
from xsight.database.repositories import get_repository
from xsight.indexer.core import sync
from xsight.embeddings.provider import OllamaEmbeddingProvider
from xsight.llm.provider import GeminiLLMProvider
from xsight.scanner.core import scan
from xsight.vectorstore.provider import QdrantVectorStoreProvider

console = Console()

HISTORY_WINDOW = 4


def run(query: str | None = typer.Argument(None), path: Path = typer.Argument(Path("."))) -> None:
    resolved_path = path.expanduser().resolve()

    conn = get_connection()
    repo_id = get_repository(resolved_path, conn)

    if repo_id is None:
        conn.close()
        console.print("[red]Repository hasn't been indexed. Run [bold]`xsight init`[/bold] first.[/red]")
        raise typer.Exit(1)

    console.rule(style="green")
    console.print("[bold cyan]XSight[/bold cyan] [dim]v0.1.0[/dim]", justify="center")
    console.print("[bold white]AI Repository Assistant[/bold white]", justify="center")
    console.rule(style="green")
    console.print()

    scan_result = scan(resolved_path)
    index_summary = sync(repo_id, scan_result.snapshot, conn)
    conn.commit()
    changed = bool(
        index_summary.added_files or index_summary.updated_files or index_summary.removed_files
    )

    if changed:
        console.print("[yellow]⚠ Repository has changed since the last index. [/yellow] ")
        confirmed = Prompt.ask(
            "Run [yellow]`xsight update`[/yellow] now? [violet bold](y/n)[/violet bold]"
        ).strip().lower()

        if confirmed not in ("n", "no"):
            conn.close()
            run_pipeline(resolved_path, lambda p, c: get_repository(p, c))
            scan_result = scan(resolved_path)  # fresh snapshot post-update
            conn = get_connection()
            index_summary = sync(repo_id, scan_result.snapshot, conn)
            conn.commit()

    console.print()
    python_files = [f for f in scan_result.snapshot.files if f.language == "python"]
    graph = load_repo_graph(resolved_path, repo_id, python_files, index_summary, conn)
    conn.close()
    repo_summary = build_repo_summary(resolved_path, scan_result.snapshot, graph)

    embedding_provider = OllamaEmbeddingProvider(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
    vectorstore_provider = QdrantVectorStoreProvider(
        collection_name=settings.qdrant_collection,
        url=settings.qdrant_url,
    )

    if settings.gemini_api_key is None:
        console.print("[red]✗ Error:[/red] GEMINI_API_KEY is not configured.")
        raise typer.Exit(code=1)

    llm_provider = GeminiLLMProvider(
        model=settings.gemini_model,
        api_key=settings.gemini_api_key,
    )

    history: list[ChatTurn] = []

    def cmd_help() -> None:
        console.print("[bold cyan]Available Commands[/bold cyan]")
        console.print("[cyan]" + "─" * 40 + "[/cyan]")
        console.print("  [bold green]help[/bold green]     Show this help message")
        console.print("  [bold green]history[/bold green]  Show the current conversation history")
        console.print("  [bold green]clear[/bold green]    Clear conversation history")
        console.print("  [bold green]stats[/bold green]    Show session information")
        console.print("  [bold green]exit[/bold green]     Leave the chat session")
        console.print("  [bold green]quit[/bold green]     Leave the chat session")

    def _preview(text: str) -> str:
        return text if len(text) <= 200 else text[:200] + "..."

    def cmd_history() -> None:
        if not history:
            console.print("[yellow]○[/yellow] No conversation history yet.")
            return
        for i, turn in enumerate(history, start=1):
            console.print(f"[bold cyan]{i}. User:[/bold cyan] {turn.question}")
            console.print(f"   [bold green]Assistant:[/bold green] {_preview(turn.answer)}")

    def cmd_clear() -> None:
        history.clear()
        console.print("[green]✓[/green] Conversation history cleared.")

    def cmd_stats() -> None:
        console.print(f"[bold cyan]Repository[/bold cyan]      : {resolved_path}")
        console.print(f"[bold cyan]Repo ID[/bold cyan]         : {repo_id}")
        console.print(f"[bold cyan]Conversation turns[/bold cyan] : {len(history)}")
        console.print(f"[bold cyan]History window[/bold cyan]  : {HISTORY_WINDOW}")
        console.print(f"[bold cyan]Graph nodes[/bold cyan]     : [bold green]{graph.number_of_nodes()}[/bold green]")
        console.print(f"[bold cyan]Graph edges[/bold cyan]     : [bold green]{graph.number_of_edges()}[/bold green]")

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
                repo_summary=repo_summary,
            )
        except NoResultsError:
            console.print("[red]Repository hasn't been indexed. Run [bold]`xsight init`[/bold] first.[/red]")
            return
        except genai_errors.APIError as e:
            console.print(f"[red bold]✗ Gemini API error ({e.code}) [/red bold]: {e.message}")
            console.print("[red]Check your GEMINI_API_KEY and network connection.[/red]")
            return
        console.print(Markdown(answer))
        history.append(ChatTurn(question=q, answer=answer))
        del history[:-HISTORY_WINDOW]

    if query is not None:
        ask(query)
        return

    console.print("\n[cyan]Type [bold]'exit'[/bold] or [bold]'quit'[/bold]' to leave.[/cyan]")

    style = Style.from_dict(
        {
            "prompt": "bold cyan",
            "": "bold ansigreen",
        }
    )

    while True:
        try:
            user_input = prompt(
                [("class:prompt", "> ")],
                style=Style.from_dict({
                    "prompt": "bold cyan",
                    "": "bold ansigreen",
                })
            ).strip()
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