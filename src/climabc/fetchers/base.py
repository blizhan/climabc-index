"""Base fetcher interface with template method pattern."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

import httpx
import numpy as np
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential


class BaseFetcher(ABC):
    """Abstract base class for all data fetchers using template method pattern.

    The fetch workflow is controlled by the fetch() method (template method).
    Subclasses can customize behavior by overriding specific methods:

    Required overrides:
    - source (property): Return source identifier
    - _parse_data: Parse raw text into DataFrame with timestamp/value columns

    Optional overrides:
    - _build_url: Build full URL from config (default: base_url + url path)
    - _preprocess_data: Transform parsed data before normalization
    - _normalize_data: Add metadata columns (default: adds source/indicator/unit)
    - validate_data: Validate data quality (default: checks required columns)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.source_config = config.get("sources", {}).get(self.source, {})
        self.client = self._create_client()

    @property
    @abstractmethod
    def source(self) -> str:
        """Return source identifier (e.g., 'psl', 'ncei')."""
        pass

    @property
    def indicators(self) -> list[str]:
        """Return list of supported indicator IDs."""
        return list(self.source_config.get("indicators", {}).keys())

    async def fetch(self, indicator: str) -> pd.DataFrame:
        """Fetch data for a specific indicator (template method).

        This method defines the workflow and calls customizable steps:
        1. Get configuration
        2. Build URL
        3. Fetch raw data (HTTP)
        4. Parse data
        5. Preprocess (optional)
        6. Normalize
        7. Validate

        Args:
            indicator: Indicator ID (e.g., 'nino34a', 'pdo')

        Returns:
            Normalized DataFrame with standardized columns

        Raises:
            ValueError: If indicator is not supported
            FetchError: If data fetching fails
            ParseError: If data parsing fails
            ValidationError: If data validation fails
        """
        # Step 1: Get configuration
        if indicator not in self.indicators:
            raise ValueError(
                f"Unknown indicator: {indicator}. "
                f"Available: {', '.join(self.indicators)}"
            )
        config = self.get_indicator_config(indicator)

        # Step 2: Build URL
        url = self._build_url(config)

        # Step 3: Fetch raw data
        try:
            raw_text = await self._fetch_with_retry(url)
        except Exception as e:
            raise FetchError(f"Failed to fetch {indicator} from {url}: {e}")

        # Step 4-7: Parse, preprocess, normalize, validate
        try:
            df = self._parse_data(raw_text, config)
            df = self._preprocess_data(df, config)
            df = self._normalize_data(df, indicator)
            self.validate_data(df, indicator)
            return df
        except Exception as e:
            if isinstance(e, (ParseError, ValidationError)):
                raise
            raise ParseError(f"Failed to process {indicator}: {e}")

    def get_indicator_config(self, indicator: str) -> Dict[str, Any]:
        """Get merged configuration for a specific indicator."""
        default_config = self.source_config.get("default", {})
        indicator_config = self.source_config.get("indicators", {}).get(indicator, {})

        merged = default_config.copy()
        merged.update(indicator_config)
        return merged

    def _build_url(self, config: Dict[str, Any]) -> str:
        """Build full URL from configuration.

        Default implementation: base_url + url path
        Override for custom URL building logic (e.g., dynamic URLs)
        """
        base_url = self.source_config.get("base_url", "")
        url_path = config.get("url", "")

        if not url_path:
            raise ValueError("No URL path configured for indicator")

        return f"{base_url.rstrip('/')}/{url_path.lstrip('/')}"

    def _create_client(self) -> httpx.AsyncClient:
        """Create async HTTP client with timeout."""
        timeout = httpx.Timeout(30.0, connect=10.0)

        return httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "ClimABC-Index/0.1.0 (Climate Data Aggregation)"},
        )

    async def _fetch_with_retry(self, url: str) -> str:
        """Fetch URL content with exponential backoff retry."""

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            reraise=True,
        )
        async def _fetch():
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text

        return await _fetch()

    @abstractmethod
    def _parse_data(self, raw_text: str, config: Dict[str, Any]) -> pd.DataFrame:
        """Parse raw text data into DataFrame.

        Must be implemented by subclasses.

        Args:
            raw_text: Raw text content from HTTP response
            config: Indicator configuration

        Returns:
            DataFrame with at least 'timestamp' and 'value' columns
        """
        pass

    def _preprocess_data(
        self, df: pd.DataFrame, config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Preprocess parsed data before normalization.

        Default: no preprocessing
        Override for: filtering, missing value handling, transformations
        """
        return df

    def _normalize_data(self, df: pd.DataFrame, indicator: str) -> pd.DataFrame:
        """Normalize data to standard schema.

        Default implementation adds metadata columns.
        Override for custom normalization logic.
        """
        config = self.get_indicator_config(indicator)

        result = pd.DataFrame()
        result["timestamp"] = pd.to_datetime(df["timestamp"])
        result["value"] = pd.to_numeric(df["value"], errors="coerce")
        result["source"] = self.source
        result["indicator"] = indicator
        result["unit"] = config.get("unit", "unknown")

        result = result.dropna(subset=["value"])

        return result.sort_values("timestamp").reset_index(drop=True)

    def validate_data(self, df: pd.DataFrame, indicator: str) -> bool:
        """Validate fetched data.

        Default: checks required columns and non-empty
        Override for: value range checks, consistency checks, etc.
        """
        required_columns = ["timestamp", "value"]
        missing = [col for col in required_columns if col not in df.columns]

        if missing:
            raise ValidationError(f"Missing required columns: {missing}")

        if df.empty:
            raise ValidationError(f"No data returned for {indicator}")

        return True

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    @staticmethod
    def _is_valid_year(year_str: Union[str, int, float]) -> bool:
        """Check if value is a valid year string (1-2200)."""
        try:
            year = int(float(year_str))
            return 1 <= year <= 2200
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _replace_missing_with_nan(
        df: pd.DataFrame, missing_value: Optional[float] = None
    ) -> pd.DataFrame:
        """Replace missing value markers with NaN."""
        if missing_value is not None:
            df = df.replace(missing_value, np.nan)
        return df

    @staticmethod
    def _wide_to_long_transform(df: pd.DataFrame, id_col: str = "year") -> pd.DataFrame:
        """Transform wide format (year x months) to long format."""
        value_cols = [c for c in df.columns if c != id_col]

        # Convert id_col to numeric first, coercing invalid values (like missing markers) to NaN
        df = df.copy()
        df[id_col] = pd.to_numeric(df[id_col], errors='coerce')

        # Filter out rows with invalid years (NaN or out of valid range 1-2200)
        df = df.dropna(subset=[id_col])
        df = df[df[id_col].astype(float).between(1, 2200)]

        long_df = df.melt(
            id_vars=[id_col],
            value_vars=value_cols,
            var_name="month",
            value_name="value",
        )

        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }

        def parse_month(m):
            if isinstance(m, str):
                try:
                    return int(m)
                except ValueError:
                    return month_map.get(m.lower(), 1)
            return int(m)

        long_df["month"] = long_df["month"].apply(parse_month)
        long_df[id_col] = long_df[id_col].astype(int)

        long_df["timestamp"] = long_df.apply(
            lambda row: pd.Timestamp(
                year=int(row[id_col]), month=int(row["month"]), day=15
            ),
            axis=1,
        )

        long_df = long_df.dropna(subset=["value"])

        return long_df[["timestamp", "value"]].sort_values("timestamp")


class FetchError(Exception):
    """Exception raised when data fetching fails."""

    pass


class ValidationError(Exception):
    """Exception raised when data validation fails."""

    pass


class ParseError(Exception):
    """Exception raised when data parsing fails."""

    pass
