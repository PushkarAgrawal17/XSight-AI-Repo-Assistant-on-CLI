"""`xsight help` command — static, curated CLI landing page.

Purely presentational. No database, no graph, no filesystem access, no LLM.
Establishes the visual style convention for XSight's CLI: bold cyan for
titles/section headings, green for command names, dim for examples/metadata.
Future commands should follow this same visual language.
"""

from rich.console import Console
from rich.table import Table

console = Console()

# Style convention (reused across future commands):
#   page title / rule   -> bold cyan
#   section heading      -> bold cyan
#   command name          -> bold green
#   description            -> default (neutral)
#   examples/metadata       -> dim
#   success                   -> bold green
#   warning                    -> bold yellow
#   error                       -> bold red


def _command_table(rows: list[tuple[str, str]]) -> Table:
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 2))
    table.add_column(style="bold green", no_wrap=True)
    table.add_column(style="default")
    for name, description in rows:
        table.add_row(name, description)
    return table


def run() -> None:
    console.rule("[bold cyan]XSight — AI Repository Assistant[/bold cyan]")
    console.print()

    console.print("[bold cyan]Repository Management[/bold cyan]")
    console.print(_command_table([
        ("init", "Index a repository"),
        ("update", "Update an indexed repository"),
    ]))
    console.print()

    console.print("[bold cyan]Repository Exploration[/bold cyan]")
    console.print(_command_table([
        ("architecture", "Repository architecture overview"),
        ("stats", "Repository statistics"),
        ("modules", "List repository modules"),
        ("symbols", "List classes, functions and methods"),
        ("dependencies", "Inspect module dependencies"),
        ("graph", "Inspect the internal graph"),
    ]))
    console.print()

    console.print("[bold cyan]AI[/bold cyan]")
    console.print(_command_table([
        ("chat", "Ask questions about the repository"),
    ]))
    console.print()

    console.print("[bold cyan]Utility[/bold cyan]")
    console.print(_command_table([
        ("help", "Show this help page"),
    ]))
    console.print()

    console.print("[bold cyan]Examples[/bold cyan]")
    console.print("[dim]  xsight init .[/dim]")
    console.print("[dim]  xsight update[/dim]")
    console.print("[dim]  xsight architecture[/dim]")
    console.print("[dim]  xsight modules[/dim]")
    console.print("[dim]  xsight chat[/dim]")
    console.print()