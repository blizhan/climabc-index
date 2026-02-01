"""PSL fetcher implementation for NOAA Physical Sciences Laboratory data."""

import io
from typing import Any, Dict

import pandas as pd

from .base import BaseFetcher


class PSLFetcher(BaseFetcher):
    """Fetcher for NOAA PSL climate data.

    Uses template method pattern - only overrides data-specific methods:
    - source (required)
    - _parse_data (required)
    - _preprocess_data (optional - handles missing values and year filtering)
    """

    @property
    def source(self) -> str:
        return "psl"

    def _parse_data(self, raw_text: str, config: Dict[str, Any]) -> pd.DataFrame:
        """Parse PSL space-delimited data format into wide format."""
        skiprows = config.get("skiprows", [])
        columns = config.get(
            "columns",
            ["year", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
        )

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

        # Transform from wide to long format
        df = self._wide_to_long_transform(df, id_col="year")

        return df

    def _preprocess_data(
        self, df: pd.DataFrame, config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Filter valid years and handle missing values."""
        # Filter valid years
        df = self._filter_valid_years(df)

        # Replace missing values with NaN
        missing_value = config.get("missing")
        if missing_value is not None:
            df = self._replace_missing_with_nan(df, missing_value)

        # Drop rows with NaN
        df = df.dropna(how="any")

        return df

    def _filter_data_lines(self, raw_text: str, skiprows: list) -> list:
        """Filter and clean raw text lines."""
        lines = []
        for i, line in enumerate(raw_text.strip().split("\n")):
            if i in skiprows:
                continue

            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            if "STOP" in stripped.upper():
                break

            lines.append(stripped)

        return lines

    def _filter_valid_years(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter rows with valid years using base class method."""
        if "year" not in df.columns:
            return df

        mask = df["year"].apply(self._is_valid_year)
        return df[mask].copy()
