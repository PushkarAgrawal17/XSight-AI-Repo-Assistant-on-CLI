from pathlib import Path

import typer
from google.genai import errors as genai_errors
from rich.console import Console

from xsight.chat.prompt import build_prompt
from xsight.config.settings import settings
from xsight.database.connection import get_connection
from xsight.database.repositories import get_repository
from xsight.embeddings.provider import OllamaEmbeddingProvider
from xsight.expansion.core import expand
from xsight.graph.builder import build
from xsight.llm.provider import GeminiLLMProvider
from xsight.parser.core import parse
from xsight.retrieval.core import search
from xsight.scanner.core import scan
from xsight.vectorstore.provider import QdrantVectorStoreProvider

console = Console()

K = 5


def run(query: str, path: Path = typer.Argument(Path("."))) -> None:
    resolved_path = path.expanduser().resolve()

    conn = get_connection()
    print(f"Resolved path: {resolved_path}")
    repo_id = get_repository(resolved_path, conn)
    print(f"Repo ID: {repo_id}")
    conn.close()

    if repo_id is None:
        console.print("[red]Repository hasn't been indexed. Run `xsight init` first.[/red]")
        raise typer.Exit(1)

    scan_result = scan(resolved_path)
    python_files = [f for f in scan_result.snapshot.files if f.language == "python"]
    modules = [
        parse(resolved_path / f.relative_path, f.relative_path) for f in python_files
    ]
    graph = build(modules)

    embedding_provider = OllamaEmbeddingProvider(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
    vectorstore_provider = QdrantVectorStoreProvider(
        collection_name=settings.qdrant_collection,
        url=settings.qdrant_url,
    )

    results = search(
        query=query,
        repo_id=repo_id,
        k=K,
        embedding_provider=embedding_provider,
        vectorstore_provider=vectorstore_provider,
    )

    if not results:
        console.print(
            "[yellow]No indexed code was found for this repository. "
            "Run `xsight init` again.[/yellow]"
        )
        raise typer.Exit(1)

    expanded = expand(results, graph)
    prompt = build_prompt(query, expanded)

    if settings.gemini_api_key is None:
        console.print("[red]Error:[/red] GEMINI_API_KEY is not configured.")
        raise typer.Exit(code=1)

    llm_provider = GeminiLLMProvider(
        model=settings.gemini_model,
        api_key=settings.gemini_api_key,
    )

    llm_provider = GeminiLLMProvider(
        model=settings.gemini_model,
        api_key=settings.gemini_api_key,
    )

    try:
        answer = llm_provider.generate(prompt)
    except genai_errors.APIError as e:
        console.print(
            f"[red]Gemini API error ({e.code}): {e.message}[/red]\n"
            "[red]Check your GEMINI_API_KEY and network connection.[/red]"
        )
        raise typer.Exit(1)

    console.print(answer)