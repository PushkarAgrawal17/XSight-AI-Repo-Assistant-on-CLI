"""XSight CLI entrypoint."""

import typer

from xsight.cli.commands import init as init_command
from xsight.cli.commands import update as update_command
from xsight.cli.commands import chat as chat_command
from xsight.cli.commands import architecture as architecture_command
from xsight.cli.commands import modules as modules_command
from xsight.cli.commands import dependencies as dependencies_command
from xsight.cli.commands import symbols as symbols_command
from xsight.cli.commands import graph as graph_command
from xsight.cli.commands import stats as stats_command
from xsight.cli.commands import help as help_command
from xsight.cli.commands import repos as repos_command
from xsight.cli.commands import remove as remove_command
from xsight.cli.commands import doctor as doctor_command
from xsight.cli.commands import config as config_command
from xsight.cli.commands import version as version_command

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
app.command(name="graph")(graph_command.run)
app.command(name="stats")(stats_command.run)
app.command(name="help")(help_command.run)
app.command(name="repos")(repos_command.run)
app.command(name="remove")(remove_command.run)
app.command(name="doctor")(doctor_command.run)
app.command(name="config")(config_command.run)
app.command(name="version")(version_command.run)


@app.callback()
def main() -> None:
    """XSight — Agentic AI-powered Code Intelligence System using Graph RAG."""


if __name__ == "__main__":
    app()