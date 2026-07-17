"""`xsight help` command — static, curated CLI landing page.

Purely presentational. No database, no graph, no filesystem access, no LLM.
Establishes the visual style convention for XSight's CLI: bold cyan for
titles/section headings, green for command names, dim for examples/metadata.
Future commands should follow this same visual language.
"""

from rich.console import Console
from rich.table import Table

console = Console()


def _command_table(rows: list[tuple[str, str]]) -> Table:
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        expand=False,
    )

    table.add_column(style="bold green", no_wrap=True)
    table.add_column()

    for command, description in rows:
        table.add_row(f"xsight {command}", description)

    return table


def _section(title: str, rows: list[tuple[str, str]]) -> None:
    console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print("[cyan]" + "─" * 55 + "[/cyan]")
    console.print(_command_table(rows))
    console.print()


def run() -> None:
    console.rule(style="green")
    console.print(
        "[bold cyan]XSight[/bold cyan] [dim]v0.1.0[/dim]",
        justify="center",
    )
    console.print(
        "[white]AI Repository Assistant[/white]",
        justify="center",
    )
    console.rule(style="green")


    _section(
        "Repository Management",
        [
            ("init", "Index a repository"),
            ("update", "Update an indexed repository"),
        ],
    )

    _section(
        "Repository Exploration",
        [
            ("architecture", "Show repository architecture"),
            ("stats", "Show repository statistics"),
            ("modules", "List repository modules"),
            ("symbols", "List repository symbols"),
            ("dependencies", "Inspect module dependencies"),
            ("graph", "Inspect the internal graph"),
        ],
    )

    _section(
        "AI",
        [
            ("chat", "Ask questions about the repository"),
        ],
    )

    _section(
        "Utilities",
        [
            ("help", "Show this help page"),
        ],
    )

    console.print("[bold cyan]Quick Start[/bold cyan]")
    console.print("[cyan]" + "─" * 55 + "[/cyan]")
    console.print("[green]  xsight init .[/green]")
    console.print("[green]  xsight update[/green]")
    console.print("[green]  xsight architecture[/green]")
    console.print("[green]  xsight modules[/green]")
    console.print("[green]  xsight chat[/green]")
    console.print()

    console.print("[bold]More information[/bold]")
    console.print("  [green]xsight <command> --help[/green]")
    console.print()