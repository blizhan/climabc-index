"""JAMSTEC forecast source implementation."""

from __future__ import annotations

import io
from typing import Any

import pandas as pd

from .base import BaseForecastFetcher, _build_static_url, _current_month_start


def _parse_jamstec_dmi_batch(raw_csv: str) -> dict[str, Any] | None:
    """Parse JAMSTEC DMI CSV into one forecast batch."""
    df = pd.read_csv(io.StringIO(raw_csv), parse_dates=["time"])
    if df.empty or "time" not in df.columns:
        return None

    df = df.sort_values("time").set_index("time")
    release_rows = df[df.isna().all(axis=1)]
    if release_rows.empty:
        return None

    release_month = release_rows.index[0]
    forecast_df = df[df.index > release_month].copy()
    if forecast_df.empty:
        return None

    value_column = "Mean" if "Mean" in forecast_df.columns else None
    if value_column is None:
        for candidate in forecast_df.columns:
            if candidate.lower() == "obs":
                continue
            value_column = candidate
            break
    if value_column is None:
        return None

    forecast_df[value_column] = pd.to_numeric(forecast_df[value_column], errors="coerce")
    forecast_df = forecast_df.dropna(subset=[value_column])
    if forecast_df.empty:
        return None

    target_dates = forecast_df.index.to_series().dt.strftime("%Y-%m").tolist()
    values = forecast_df[value_column].astype(float).tolist()
    data_points = [{"dmi": value} for value in values]

    return {
        "id": f"forecast-jamstec-{release_month.strftime('%Y-%m')}",
        "source": "jamstec",
        "issuedDate": release_month.strftime("%Y-%m"),
        "targetDates": target_dates,
        "data": data_points,
        "isHistorical": release_month < _current_month_start(),
    }


class JamstecForecastFetcher(BaseForecastFetcher):
    """JAMSTEC DMI forecast fetcher."""

    @property
    def source(self) -> str:
        return "jamstec"

    async def fetch_batch(self) -> dict[str, Any] | None:
        indicator_config = self.source_config.get("indicators", {}).get("dmi")
        if not indicator_config:
            return None

        url = _build_static_url(self.source_config, indicator_config)
        response = await self.client.get(url)
        response.raise_for_status()
        return _parse_jamstec_dmi_batch(response.text)
