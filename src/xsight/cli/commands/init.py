"""`xsight init` command."""

from pathlib import Path

import requests
import typer
from rich.console import Console

from xsight.chunker.core import chunk
from xsight.config.settings import settings
from xsight.database.connection import get_connection
from xsight.database.repositories import get_or_create_repository
from xsight.embeddings.core import embed
from xsight.embeddings.provider import OllamaEmbeddingProvider
from xsight.graph.builder import build
from xsight.graph.enrichment import add_calls_edges, add_import_edges
from xsight.imports.core import resolve_imports
from xsight.calls.core import resolve_calls
from xsight.indexer.core import sync
from xsight.parser.core import parse
from xsight.scanner.core import scan
from xsight.vectorstore.core import create_collection, upsert
from xsight.vectorstore.provider import QdrantVectorStoreProvider

console = Console()


def run(
    path: Path = typer.Argument(
        Path("."),
        help="Path to the repository to index. Defaults to the current directory.",
    ),
) -> None:
    """Index a repository: scan, parse, build a knowledge graph, and embed it."""
    resolved_path = path.expanduser().resolve()
    if not resolved_path.is_dir():
        console.print(f"[red]Error:[/red] '{resolved_path}' is not a directory.")
        raise typer.Exit(code=1)

    embedding_provider = OllamaEmbeddingProvider(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
    vector_provider = QdrantVectorStoreProvider(
        collection_name=settings.qdrant_collection,
        url=settings.qdrant_url,
    )

    conn = get_connection()
    try:
        console.print("[bold]Scanning repository...[/bold]")
        result = scan(resolved_path)

        console.print("[bold]Syncing metadata...[/bold]")
        repo_id = get_or_create_repository(result.snapshot.repo_path, conn)
        index_summary = sync(repo_id, result.snapshot, conn)

        console.print("[bold]Parsing source files...[/bold]")
        python_files = [f for f in result.snapshot.files if f.language == "python"]
        modules = [
            parse(resolved_path / f.relative_path, f.relative_path)
            for f in python_files
        ]

        console.print("[bold]Building knowledge graph...[/bold]")
        graph = build(modules)

        console.print("[bold]Resolving imports...[/bold]")
        import_edges = resolve_imports(modules)
        add_import_edges(graph, import_edges)

        console.print("[bold]Resolving calls...[/bold]")
        call_edges = resolve_calls(modules)
        add_calls_edges(graph, call_edges)

        console.print("[bold]Chunking symbols...[/bold]")
        chunks = chunk(graph, resolved_path)

        console.print(f"[bold]Generating embeddings for {len(chunks)} chunks...[/bold]")
        try:
            embedded = embed(chunks, embedding_provider)
        except requests.exceptions.ConnectionError as e:
            console.print(
                "[red]Error:[/red] Could not reach Ollama.\n"
                "  Start it with: [bold]ollama serve[/bold]\n"
                f"  Make sure the model is pulled: [bold]ollama pull {settings.embedding_model}[/bold]\n"
                f"  ({e})"
            )
            raise typer.Exit(code=1)

        console.print("[bold]Storing vectors...[/bold]")
        try:
            create_collection(embedding_provider.dimension, vector_provider)
            upsert(embedded, repo_id, vector_provider)
        except Exception as e:
            console.print(
                "[red]Error:[/red] Could not reach Qdrant.\n"
                "  Start it with: [bold]docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant[/bold]\n"
                f"  ({e})"
            )
            raise typer.Exit(code=1)
    finally:
        conn.close()

    _render_summary(resolved_path, result.summary, index_summary, len(chunks))


def _render_summary(repo_path: Path, scan_summary, index_summary, chunk_count: int) -> None:
    console.print(f"\n[bold green]Indexed[/bold green] {repo_path}")
    console.print(
        f"  files: {index_summary.total_files} total "
        f"([green]+{index_summary.added}[/green] "
        f"[yellow]~{index_summary.updated}[/yellow] "
        f"[red]-{index_summary.removed}[/red] "
        f"={index_summary.unchanged})"
    )
    console.print(
        f"  skipped: {scan_summary.ignored_files} ignored files, "
        f"{scan_summary.ignored_directories} ignored dirs, "
        f"{scan_summary.skipped_binary_files} binary, "
        f"{scan_summary.skipped_large_files} too large"
    )
    if scan_summary.errors:
        console.print(f"  [red]{scan_summary.errors} files skipped due to errors[/red]")
    console.print(f"  chunks embedded: {chunk_count}")