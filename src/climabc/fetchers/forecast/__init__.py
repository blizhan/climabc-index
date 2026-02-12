"""Forecast source integrations for CLI data generation."""

from __future__ import annotations

from typing import Any

import click

from .base import (
    BaseForecastFetcher,
    _resolve_template_params,
    _values_to_batch,
)
from .iri import (
    IriForecastFetcher,
    _extract_iri_issue_date,
    _extract_iri_nino34_values,
)
from .jamstec import (
    JamstecForecastFetcher,
    _parse_jamstec_dmi_batch,
)


def _build_forecast_fetchers(config: dict[str, Any]) -> list[BaseForecastFetcher]:
    """Create forecast fetcher instances for configured forecast sources."""
    sources = config.get("sources", {})
    fetchers: list[BaseForecastFetcher] = []

    if sources.get("iri", {}).get("type") == "forecast":
        fetchers.append(IriForecastFetcher(config))
    if sources.get("jamstec", {}).get("type") == "forecast":
        fetchers.append(JamstecForecastFetcher(config))

    for source_name, source_config in sources.items():
        if source_config.get("type") != "forecast":
            continue
        if source_name not in {"iri", "jamstec"}:
            click.echo(
                f"  ⚠ Forecast source '{source_name}' is configured but not yet mapped to frontend metrics",
                err=True,
            )

    return fetchers


def _resolve_source_batch_limit(fetcher: BaseForecastFetcher) -> int:
    """Resolve how many recent batches should be fetched for one source."""
    source_default = 36 if fetcher.source == "iri" else 1
    raw_limit = fetcher.source_config.get("recent_batches", source_default)
    try:
        return max(1, int(raw_limit))
    except (TypeError, ValueError):
        return source_default


async def fetch_forecast_batches(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch forecast batches from configured forecast fetchers."""
    fetchers = _build_forecast_fetchers(config)
    if not fetchers:
        return []

    batches: list[dict[str, Any]] = []
    for fetcher in fetchers:
        try:
            batch_limit = _resolve_source_batch_limit(fetcher)
            async with fetcher:
                source_batches = await fetcher.fetch_batches(max_batches=batch_limit)
            batches.extend(source_batches)
        except Exception as exc:  # noqa: BLE001
            click.echo(
                f"  ⚠ Failed to fetch forecast source '{fetcher.source}': {exc}",
                err=True,
            )

    batches.sort(key=lambda item: item.get("issuedDate", ""), reverse=True)
    return batches


__all__ = [
    "BaseForecastFetcher",
    "IriForecastFetcher",
    "JamstecForecastFetcher",
    "fetch_forecast_batches",
    "_resolve_template_params",
    "_extract_iri_issue_date",
    "_extract_iri_nino34_values",
    "_parse_jamstec_dmi_batch",
    "_values_to_batch",
]
