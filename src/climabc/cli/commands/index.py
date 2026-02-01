"""Index-related CLI commands."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import click
import pandas as pd
import yaml

from climabc.fetchers import NCEIFetcher, PSLFetcher


FETCHERS = {
    "ncei": NCEIFetcher,
    "psl": PSLFetcher,
}


def _config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "indicators.yaml"


def load_config() -> Dict[str, Any]:
    """Load indicator configuration from YAML."""
    path = _config_path()
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def iter_indicators(
    config: Dict[str, Any], source: Optional[str] = None
) -> Iterable[Tuple[str, str, Dict[str, Any]]]:
    """Yield (source, indicator_id, indicator_config)."""
    sources = config.get("sources", {})
    for source_id, source_config in sources.items():
        if source and source_id != source:
            continue
        indicators = source_config.get("indicators", {})
        for indicator_id, indicator_config in indicators.items():
            yield source_id, indicator_id, indicator_config


def resolve_indicator_source(
    config: Dict[str, Any], indicator: str, source: Optional[str]
) -> str:
    """Resolve the source for an indicator, validating user input."""
    matches = [
        source_id
        for source_id, indicator_id, _ in iter_indicators(config)
        if indicator_id == indicator
    ]

    if not matches:
        raise click.ClickException(f"Unknown indicator: {indicator}")

    if source:
        if source not in matches:
            raise click.ClickException(
                f"Indicator '{indicator}' not available for source '{source}'."
            )
        return source

    if len(matches) > 1:
        raise click.ClickException(
            f"Indicator '{indicator}' exists in multiple sources: {', '.join(matches)}. "
            "Please specify --source."
        )

    return matches[0]


async def _fetch_indicator(config: Dict[str, Any], indicator: str, source: str) -> pd.DataFrame:
    fetcher_class = FETCHERS.get(source)
    if not fetcher_class:
        raise click.ClickException(f"No fetcher available for source '{source}'.")

    async with fetcher_class(config) as fetcher:
        return await fetcher.fetch(indicator)


async def _fetch_all(
    config: Dict[str, Any], sources: List[str]
) -> List[Tuple[str, str, pd.DataFrame, Optional[Exception]]]:
    results: List[Tuple[str, str, pd.DataFrame, Optional[Exception]]] = []

    for source in sources:
        fetcher_class = FETCHERS.get(source)
        if not fetcher_class:
            for _, indicator_id, _ in iter_indicators(config, source=source):
                results.append(
                    (source, indicator_id, pd.DataFrame(), RuntimeError("fetcher missing"))
                )
            continue

        async with fetcher_class(config) as fetcher:
            indicators = list(fetcher.indicators)
            tasks = [fetcher.fetch(indicator) for indicator in indicators]
            fetched = await asyncio.gather(*tasks, return_exceptions=True)
            for indicator_id, result in zip(indicators, fetched):
                if isinstance(result, Exception):
                    results.append((source, indicator_id, pd.DataFrame(), result))
                else:
                    results.append((source, indicator_id, result, None))

    return results


@click.group()
def index() -> None:
    """Index data operations."""


@index.command("list")
@click.option("--source", help="Filter indicators by source.")
def list_indicators(source: Optional[str]) -> None:
    """List all configured indicators."""
    config = load_config()

    rows = [
        (source_id, indicator_id, indicator_config.get("name", ""))
        for source_id, indicator_id, indicator_config in iter_indicators(config, source)
    ]

    if not rows:
        raise click.ClickException("No indicators found for the specified filter.")

    header = ("Source", "Indicator", "Name")
    click.echo(f"{header[0]:<10} {header[1]:<18} {header[2]}")
    click.echo("-" * 60)
    for source_id, indicator_id, name in sorted(rows):
        click.echo(f"{source_id:<10} {indicator_id:<18} {name}")


@index.command("fetch")
@click.argument("indicator")
@click.option("--source", help="Specify the data source for the indicator.")
def fetch_indicator(indicator: str, source: Optional[str]) -> None:
    """Fetch a specific indicator and print a preview."""
    config = load_config()
    resolved_source = resolve_indicator_source(config, indicator, source)

    df = asyncio.run(_fetch_indicator(config, indicator, resolved_source))

    click.echo(f"Fetched {len(df)} records for {indicator} ({resolved_source}).")
    click.echo(df.tail(10).to_string(index=False))


@index.command("fetch-all")
@click.option("--source", help="Limit fetch to a specific source.")
def fetch_all(source: Optional[str]) -> None:
    """Fetch all indicators."""
    config = load_config()
    sources = [source] if source else list(config.get("sources", {}).keys())

    results = asyncio.run(_fetch_all(config, sources))

    for source_id, indicator_id, df, error in results:
        if error:
            click.echo(
                f"{source_id}:{indicator_id} - failed ({type(error).__name__}: {error})"
            )
            continue

        latest_value = df.iloc[-1]["value"] if not df.empty else "n/a"
        click.echo(
            f"{source_id}:{indicator_id} - {len(df)} records (latest: {latest_value})"
        )


@index.command("status")
def status() -> None:
    """Show data source status."""
    config = load_config()
    sources = config.get("sources", {})

    header = ("Source", "Indicators", "Fetcher")
    click.echo(f"{header[0]:<10} {header[1]:<12} {header[2]}")
    click.echo("-" * 40)

    for source_id, source_config in sorted(sources.items()):
        indicator_count = len(source_config.get("indicators", {}))
        fetcher_status = "available" if source_id in FETCHERS else "missing"
        click.echo(f"{source_id:<10} {indicator_count:<12} {fetcher_status}")
