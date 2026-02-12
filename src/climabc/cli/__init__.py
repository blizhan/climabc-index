"""Command-line interface for ClimABC."""

import click

from climabc.cli.commands.generate import generate, mock
from climabc.cli.commands.index import index


@click.group()
def cli() -> None:
    """Run ClimABC CLI commands."""


cli.add_command(index)
cli.add_command(generate)
cli.add_command(mock)

__all__ = ["cli"]
