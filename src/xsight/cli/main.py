"""XSight CLI entrypoint."""

import typer

from xsight.cli.commands import init as init_command
from xsight.cli.commands import update as update_command
from xsight.cli.commands import chat as chat_command
from xsight.cli.commands import architecture as architecture_command
from xsight.cli.commands import modules as modules_command
from xsight.cli.commands import dependencies as dependencies_command
from xsight.cli.commands import symbols as symbols_command

app = typer.Typer(
    name="xsight",
    help="Agentic AI-powered Code Intelligence System using Graph RAG.",
    no_args_is_help=True,
)

app.command(name="init")(init_command.run)
app.command(name="update")(update_command.run)
app.command(name="chat")(chat_command.run)
app.command(name="architecture")(architecture_command.run)
app.command(name="modules")(modules_command.run)
app.command(name="dependencies")(dependencies_command.run)
app.command(name="symbols")(symbols_command.run)


@app.callback()
def main() -> None:
    """XSight — Agentic AI-powered Code Intelligence System using Graph RAG."""


if __name__ == "__main__":
    app()