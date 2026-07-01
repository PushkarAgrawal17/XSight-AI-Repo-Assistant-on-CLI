"""XSight CLI entrypoint."""

import typer

from xsight.cli.commands import init as init_command

app = typer.Typer(
    name="xsight",
    help="Agentic AI-powered Code Intelligence System using Graph RAG.",
    no_args_is_help=True,
)

app.command(name="init")(init_command.run)


if __name__ == "__main__":
    app()
