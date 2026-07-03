"""XSight CLI entrypoint."""

import typer

from xsight.cli.commands import init as init_command
from xsight.cli.commands import chat as chat_command

app = typer.Typer(
    name="xsight",
    help="Agentic AI-powered Code Intelligence System using Graph RAG.",
    no_args_is_help=True,
)

app.command(name="init")(init_command.run)
app.command(name="chat")(chat_command.run)


@app.callback()
def main() -> None:
    """XSight — Agentic AI-powered Code Intelligence System using Graph RAG."""


if __name__ == "__main__":
    app()