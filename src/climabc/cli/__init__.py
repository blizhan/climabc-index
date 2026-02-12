"""Command-line interface for ClimABC."""

import click

from climabc.cli.commands.generate import _fetch_all_data, generate, mock
from climabc.cli.commands.index import index
from climabc.fetchers.forecast import fetch_forecast_batches as _fetch_forecast_batches

# Backward-compatible module-level callables used by tests and tooling.
fetch_all_data = _fetch_all_data
fetch_forecast_batches = _fetch_forecast_batches


@click.group()
def cli() -> None:
    """Run ClimABC CLI commands."""


cli.add_command(index)
cli.add_command(generate)
cli.add_command(mock)

__all__ = ["cli", "fetch_all_data", "fetch_forecast_batches"]
