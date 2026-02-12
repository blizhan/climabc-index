"""CLI commands for generating ENSO data parquet files."""

import asyncio
import json
from pathlib import Path
from typing import Any, Optional

import click
import pandas as pd
import yaml

from .fetchers.psl import PSLFetcher
from .fetchers.forecast import fetch_forecast_batches


def load_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


async def fetch_indicator(fetcher: PSLFetcher, indicator: str) -> pd.DataFrame:
    """Fetch data for a single indicator."""
    click.echo(f"  Fetching {indicator}...")
    df = await fetcher.fetch(indicator)
    click.echo(f"    ✓ Got {len(df)} rows")
    return df


async def fetch_all_data(
    config: dict[str, Any], indicators: list[str] | None = None
) -> dict[str, pd.DataFrame]:
    """Fetch indicator data, optionally scoped to a specific indicator list."""
    fetcher = PSLFetcher(config)
    available_indicators = fetcher.indicators
    requested_indicators = indicators or available_indicators

    unknown_indicators = [
        indicator for indicator in requested_indicators if indicator not in available_indicators
    ]
    if unknown_indicators:
        raise ValueError(f"Unknown indicators requested: {unknown_indicators}")

    click.echo(f"Fetching {len(requested_indicators)} indicators from PSL...")

    async with fetcher:
        tasks = [fetch_indicator(fetcher, ind) for ind in requested_indicators]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    data = {}
    for indicator, result in zip(requested_indicators, results):
        if isinstance(result, Exception):
            click.echo(f"    ✗ Failed: {result}", err=True)
        else:
            data[indicator] = result

    return data


def merge_indicators(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Merge all indicator DataFrames into wide format."""
    click.echo("Merging indicators into wide format...")

    merged = None
    for indicator, df in data.items():
        df = df.copy()
        df = df.rename(columns={"value": indicator})
        df = df[["timestamp", indicator]]

        if merged is None:
            merged = df
        else:
            merged = merged.merge(df, on="timestamp", how="outer")

    merged = merged.sort_values("timestamp").reset_index(drop=True)
    click.echo(f"  ✓ Merged {len(merged)} rows")
    return merged


def write_split_observation_files(observations: pd.DataFrame, output_dir: Path) -> None:
    """Write observation files split by metric in parquet format."""
    obs_dir = output_dir / "observations"
    obs_dir.mkdir(parents=True, exist_ok=True)

    metric_columns = [column for column in observations.columns if column != "date"]
    for metric in metric_columns:
        metric_df = observations[["date", metric]].copy()
        metric_df = metric_df.dropna(subset=[metric]).rename(columns={metric: "value"}).reset_index(drop=True)
        output_path = obs_dir / f"{metric}.parquet"
        metric_df.to_parquet(output_path, index=False)


def _infer_forecast_source(forecast_id: str) -> str:
    """Infer source name from forecast id for backward compatibility."""
    token = str(forecast_id).lower()
    if "jamstec" in token:
        return "jamstec"
    if "iri" in token:
        return "iri"
    return "unknown"


def flatten_forecast_batches(forecasts: list[dict]) -> pd.DataFrame:
    """Flatten forecast batches into long-table rows for parquet storage."""
    rows: list[dict[str, Any]] = []
    for forecast_batch in forecasts:
        forecast_id = str(forecast_batch.get("id", ""))
        source = str(forecast_batch.get("source") or _infer_forecast_source(forecast_id))
        issued_date = str(forecast_batch.get("issuedDate", ""))
        is_historical = bool(forecast_batch.get("isHistorical"))

        target_dates = forecast_batch.get("targetDates", [])
        data_points = forecast_batch.get("data", [])
        for target_date, data_point in zip(target_dates, data_points):
            if not isinstance(data_point, dict):
                continue
            for metric, raw_value in data_point.items():
                if raw_value is None:
                    continue
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    continue
                rows.append(
                    {
                        "forecast_id": forecast_id,
                        "source": source,
                        "issued_date": issued_date,
                        "target_date": str(target_date),
                        "metric": str(metric),
                        "value": value,
                        "is_historical": is_historical,
                    }
                )

    if not rows:
        return pd.DataFrame(
            columns=[
                "forecast_id",
                "source",
                "issued_date",
                "target_date",
                "metric",
                "value",
                "is_historical",
            ]
        )

    return pd.DataFrame(rows)


def write_split_forecast_files(forecasts: list[dict], output_dir: Path) -> None:
    """Write forecast files split by metric and issue batch in parquet format."""
    forecast_root = output_dir / "forecasts"
    forecast_root.mkdir(parents=True, exist_ok=True)
    forecast_df = flatten_forecast_batches(forecasts)
    if forecast_df.empty:
        return

    grouped = forecast_df.groupby(["metric", "issued_date"], dropna=False, sort=True)
    for (metric, issued_date), group_df in grouped:
        metric_dir = forecast_root / str(metric)
        metric_dir.mkdir(parents=True, exist_ok=True)
        safe_issue = str(issued_date).replace("/", "_")
        output_path = metric_dir / f"{safe_issue}.parquet"
        group_df.reset_index(drop=True).to_parquet(output_path, index=False)


def sanitize_observation_values(
    observations: pd.DataFrame,
    config: dict[str, Any],
    source_to_metric: dict[str, str],
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Replace known missing markers and detected out-of-range values with NaN."""
    cleaned = observations.copy()
    source_config = config.get("sources", {}).get("psl", {})
    source_default = source_config.get("default", {})
    indicator_config = source_config.get("indicators", {})

    stats = {"missing_replaced": 0, "outlier_replaced": 0}

    # Convert metric columns to numeric first so coercion failures become NaN.
    metric_columns = [column for column in cleaned.columns if column != "date"]
    for metric in metric_columns:
        cleaned.loc[:, metric] = pd.to_numeric(cleaned[metric], errors="coerce")

    # Replace configured missing markers.
    default_missing = source_default.get("missing")
    for source_indicator, metric in source_to_metric.items():
        if metric not in cleaned.columns:
            continue

        missing_value = indicator_config.get(source_indicator, {}).get(
            "missing", default_missing
        )
        if missing_value is None:
            continue

        try:
            missing_numeric = float(missing_value)
        except (TypeError, ValueError):
            continue

        mask = cleaned[metric] == missing_numeric
        stats["missing_replaced"] += int(mask.sum())
        cleaned.loc[mask, metric] = float("nan")

    # Replace obvious out-of-range anomalies.
    metric_ranges: dict[str, tuple[float, float]] = {
        "nino34": (-5.0, 5.0),
        "nino12": (-5.0, 5.0),
        "nino3": (-5.0, 5.0),
        "nino4": (-5.0, 5.0),
        "oni": (-5.0, 5.0),
        "dmi": (-5.0, 5.0),
        "soi": (-60.0, 60.0),
    }
    for metric, (lower, upper) in metric_ranges.items():
        if metric not in cleaned.columns:
            continue
        mask = cleaned[metric].notna() & ~cleaned[metric].between(lower, upper)
        stats["outlier_replaced"] += int(mask.sum())
        cleaned.loc[mask, metric] = float("nan")

    return cleaned, stats


@click.group()
def cli():
    """ClimABC Index CLI - Generate ENSO data for visualization."""
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to configuration file (default: src/climabc/config/indicators.yaml)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Optional output parquet file path for merged observations (default: disabled)",
)
@click.option(
    "--json-output",
    "-j",
    type=click.Path(path_type=Path),
    default=None,
    help="Optional JSON file path for frontend compatibility (default: disabled)",
)
@click.option(
    "--forecast-output",
    "-f",
    type=click.Path(path_type=Path),
    default=None,
    help="Optional output parquet file path for merged forecasts (default: disabled)",
)
@click.option(
    "--split-output-dir",
    "-s",
    type=click.Path(path_type=Path),
    default=Path("data"),
    help="Directory for split observation/forecast files",
)
def generate(
    config: Path,
    output: Optional[Path],
    json_output: Optional[Path],
    forecast_output: Optional[Path],
    split_output_dir: Path,
):
    """Generate ENSO data files from PSL sources.

    Fetches indicator data, merges into wide format, generates forecasts,
    and outputs both parquet and JSON for frontend consumption.
    """
    click.echo("=" * 50)
    click.echo("ClimABC Index - Data Generation")
    click.echo("=" * 50)

    # Load config
    if config is None:
        # Default to package config
        config = Path(__file__).parent / "config" / "indicators.yaml"

    if not config.exists():
        click.echo(f"Config file not found: {config}", err=True)
        raise click.Abort()

    click.echo(f"Config: {config}")
    cfg = load_config(config)

    # Fetch data
    # Keep generation focused on indicators required by current frontend contract.
    required_indicators = ["nino34a", "nino1a", "nino3a", "nino4a", "soi", "oni", "dmi"]
    data = asyncio.run(fetch_all_data(cfg, indicators=required_indicators))

    if not data:
        click.echo("No data fetched, aborting.", err=True)
        raise click.Abort()

    # Merge to wide format
    merged = merge_indicators(data)

    # Rename columns to match frontend expectations
    column_map = {
        "nino34a": "nino34",
        "nino1a": "nino12",
        "nino12a": "nino12",  # Backward compatibility for alternate source naming.
        "nino3a": "nino3",
        "nino4a": "nino4",
        "soi": "soi",
        "oni": "oni",
        "dmi": "dmi",
    }
    merged = merged.rename(columns=column_map)

    # Format timestamp as date string
    merged["date"] = merged["timestamp"].dt.strftime("%Y-%m")
    merged = merged.drop(columns=["timestamp"])

    # Reorder columns
    cols = ["date", "nino34", "nino12", "nino3", "nino4", "soi", "oni", "dmi"]
    merged = merged[[c for c in cols if c in merged.columns]]

    merged, sanitize_stats = sanitize_observation_values(merged, cfg, column_map)
    click.echo(
        "  ✓ Sanitized anomalies: "
        f"missing->{sanitize_stats['missing_replaced']} "
        f"outlier->{sanitize_stats['outlier_replaced']}"
    )

    # Drop rows where all core ENSO indicators are missing.
    # Keep partially available rows so one lagging indicator (e.g., DMI trailing months)
    # does not truncate newer observation dates from other indicators.
    indicator_cols = [c for c in merged.columns if c not in ("timestamp", "date", "_ts")]
    core_cols = [c for c in indicator_cols if c != "dmi"] or indicator_cols
    merged_clean = merged.dropna(subset=core_cols, how="all")
    click.echo(
        "  ✓ Cleaned rows: "
        f"{len(merged_clean)} (dropped {len(merged) - len(merged_clean)} "
        "rows where all core indicators are missing)"
    )

    # Save optional merged observation parquet.
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        merged_clean.to_parquet(output, index=False)
        click.echo(f"✓ Saved parquet: {output}")
    else:
        click.echo("✓ Skipped merged observation parquet (disabled)")

    # Fetch forecasts from real forecast sources only.
    click.echo("Fetching forecast sources...")
    forecasts = asyncio.run(fetch_forecast_batches(cfg))
    click.echo(f"  ✓ Forecast batches fetched: {len(forecasts)}")

    # Save optional merged forecast parquet.
    forecast_df = flatten_forecast_batches(forecasts)
    if forecast_output is not None:
        forecast_output.parent.mkdir(parents=True, exist_ok=True)
        forecast_df.to_parquet(forecast_output, index=False)
        click.echo(f"✓ Saved forecast parquet: {forecast_output}")
    else:
        click.echo("✓ Skipped merged forecast parquet (disabled)")

    # Prepare optional JSON output - ensure all values are JSON serializable
    def clean_value(v):
        if v is None or (isinstance(v, float) and v != v):  # NaN check
            return None
        if hasattr(v, 'item'):  # numpy scalar
            return v.item()
        if hasattr(v, 'strftime'):  # datetime/timestamp
            return v.strftime('%Y-%m-%d')
        return v

    def clean_records(records):
        return [{k: clean_value(v) for k, v in record.items() if k != "_ts"} for record in records]

    if json_output is not None:
        output_data = {
            "observations": clean_records(merged_clean.to_dict("records")),
            "forecasts": forecasts,
            "latestForecast": forecasts[0] if forecasts else None,
            "selectedForecast": None,
        }

        json_output.parent.mkdir(parents=True, exist_ok=True)
        with open(json_output, "w") as f:
            json.dump(output_data, f, indent=2, default=str)

        click.echo(f"✓ Saved JSON: {json_output}")

    # Save split datasets for downstream processing.
    write_split_observation_files(merged_clean, split_output_dir)
    write_split_forecast_files(forecasts, split_output_dir)
    click.echo(f"✓ Saved split data: {split_output_dir}")

    click.echo("=" * 50)
    click.echo("Done!")


@cli.command()
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("frontend/public"),
    help="Output directory for mock data",
)
def mock(output_dir: Path):
    """Generate mock ENSO data for development/testing.

    Creates synthetic ENSO data without requiring network access.
    """
    click.echo("Generating mock ENSO data...")

    import numpy as np

    # Generate observations
    observations = []
    start_date = pd.Timestamp("1980-01-15")
    end_date = pd.Timestamp("2024-01-15")

    dates = pd.date_range(start=start_date, end=end_date, freq="MS")

    for i, date in enumerate(dates):
        t = i / 12  # years
        observations.append({
            "date": date.strftime("%Y-%m"),
            "nino34": float(np.sin(t * 2) * 1.5 + np.random.normal(0, 0.3)),
            "nino12": float(np.sin(t * 2 + 0.5) * 2 + np.random.normal(0, 0.4)),
            "nino3": float(np.sin(t * 2 + 0.3) * 1.8 + np.random.normal(0, 0.35)),
            "nino4": float(np.sin(t * 2 + 0.7) * 1.2 + np.random.normal(0, 0.25)),
            "soi": float(np.cos(t * 2) * 10 + np.random.normal(0, 2)),
            "oni": float(np.sin(t * 2) * 1.2 + np.random.normal(0, 0.25)),
        })

    # Generate forecasts
    forecasts = []
    now = pd.Timestamp.now()
    for i in range(12):
        issue_date = now - pd.DateOffset(months=i)
        issue_date = issue_date.replace(day=1)

        target_dates = []
        forecast_data = []

        for j in range(1, 13):
            target_date = issue_date + pd.DateOffset(months=j)
            target_dates.append(target_date.strftime("%Y-%m"))

            t = (len(dates) + j) / 12
            base = np.sin(t * 2)
            error = (j / 12) * 0.5

            forecast_data.append({
                "nino34": float(base * 1.5 + np.random.normal(0, error)),
                "nino12": float(np.sin(t * 2 + 0.5) * 2 + np.random.normal(0, error)),
                "nino3": float(np.sin(t * 2 + 0.3) * 1.8 + np.random.normal(0, error)),
                "nino4": float(np.sin(t * 2 + 0.7) * 1.2 + np.random.normal(0, error)),
                "soi": float(np.cos(t * 2) * 10 + np.random.normal(0, error * 5)),
                "oni": float(np.sin(t * 2) * 1.2 + np.random.normal(0, error)),
            })

        forecasts.append({
            "id": f"forecast-{issue_date.strftime('%Y-%m')}",
            "issuedDate": issue_date.strftime("%Y-%m"),
            "targetDates": target_dates,
            "data": forecast_data,
            "isHistorical": i > 0,
        })

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)

    output_data = {
        "observations": observations,
        "forecasts": forecasts,
        "latestForecast": forecasts[0] if forecasts else None,
        "selectedForecast": None,
    }

    json_path = output_dir / "enso_data.json"
    with open(json_path, "w") as f:
        json.dump(output_data, f, indent=2)

    click.echo(f"✓ Saved mock data: {json_path}")
    click.echo(f"  Observations: {len(observations)}")
    click.echo(f"  Forecast batches: {len(forecasts)}")


if __name__ == "__main__":
    cli()
