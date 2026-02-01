"""Command-line interface for ClimABC."""

import click

from climabc.cli.commands.index import index


@click.group()
def cli() -> None:
    """Run ClimABC CLI commands."""


cli.add_command(index)

__all__ = ["cli"]
