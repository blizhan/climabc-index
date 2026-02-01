"""NCEI fetcher implementation for NOAA NCEI climate data."""

import io
from typing import Any, Dict

import pandas as pd

from .base import BaseFetcher


class NCEIFetcher(BaseFetcher):
    """Fetcher for NOAA NCEI climate data."""

    @property
    def source(self) -> str:
        return "ncei"

    def _parse_data(self, raw_text: str, config: Dict[str, Any]) -> pd.DataFrame:
        """Parse NCEI space-delimited data into a standardized format."""
        skiprows = config.get("skiprows", [])
        columns = config.get("columns", [])

        lines = self._filter_data_lines(raw_text, skiprows)

        if not lines:
            raise ValueError("No valid data lines found")

        df = pd.read_csv(
            io.StringIO("\n".join(lines)),
            sep=r"\s+",
            header=None,
            names=columns,
            on_bad_lines="skip",
            engine="python",
        )

        if "month" in columns:
            return self._parse_monthly_columns(df, columns)

        if "year" in columns:
            return self._wide_to_long_transform(df, id_col="year")

        raise ValueError("NCEI data must include a year column")

    def _preprocess_data(
        self, df: pd.DataFrame, config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Handle missing values and filter invalid years."""
        df = self._filter_valid_years(df)

        missing_value = config.get("missing")
        if missing_value is not None:
            df = self._replace_missing_with_nan(df, missing_value)

        df = df.dropna(subset=["value"])

        return df

    def _normalize_data(self, df: pd.DataFrame, indicator: str) -> pd.DataFrame:
        """Normalize data and preserve multi-indicator columns."""
        config = self.get_indicator_config(indicator)

        result = pd.DataFrame()
        result["timestamp"] = pd.to_datetime(df["timestamp"])
        result["value"] = pd.to_numeric(df["value"], errors="coerce")
        result["source"] = self.source
        result["indicator"] = df.get("indicator", indicator)
        result["unit"] = config.get("unit", "unknown")

        result = result.dropna(subset=["value"])

        return result.sort_values(["indicator", "timestamp"]).reset_index(drop=True)

    def _filter_data_lines(self, raw_text: str, skiprows: list) -> list:
        """Filter and clean raw text lines."""
        lines = []
        for i, line in enumerate(raw_text.strip().split("\n")):
            if i in skiprows:
                continue

            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            lines.append(stripped)

        return lines

    def _parse_monthly_columns(self, df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """Parse year-month formats with one or more value columns."""
        value_columns = [c for c in columns if c not in ("year", "month")]
        if not value_columns:
            raise ValueError("No value columns found for NCEI monthly data")

        df["timestamp"] = pd.to_datetime(
            {"year": df["year"], "month": df["month"], "day": 15}
        )

        if len(value_columns) == 1:
            df["value"] = df[value_columns[0]]
            return df[["timestamp", "value", "year", "month"]]

        melted = df.melt(
            id_vars=["year", "month", "timestamp"],
            value_vars=value_columns,
            var_name="indicator",
            value_name="value",
        )

        return melted[["timestamp", "value", "indicator", "year", "month"]]

    def _filter_valid_years(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter rows with valid years."""
        if "year" in df.columns:
            mask = df["year"].apply(self._is_valid_year)
            return df[mask].copy()

        if "timestamp" in df.columns:
            years = pd.to_datetime(df["timestamp"]).dt.year
            mask = years.apply(self._is_valid_year)
            return df[mask].copy()

        return df
