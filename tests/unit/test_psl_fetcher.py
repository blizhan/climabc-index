"""Tests for PSL fetcher (simplified with template method pattern)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pytest
from utils import create_fetcher_tests, create_parsing_tests

from climabc.fetchers import PSLFetcher


class TestPSLParsing:
    """Test PSL-specific parsing logic only."""

    @pytest.fixture
    def fetcher(self, config):
        return PSLFetcher(config)

    def test_parse_space_delimited_format(self, fetcher, sample_psl_data):
        """Test parsing PSL space-delimited format."""
        config = fetcher.get_indicator_config("nino34a")
        df = fetcher._parse_data(sample_psl_data, config)

        # Should produce timestamp and value columns
        assert "timestamp" in df.columns
        assert "value" in df.columns
        assert len(df) == 60  # 5 years * 12 months in sample data

    def test_filter_lines_skips_comments_and_stop(self, fetcher):
        """Test line filtering removes comments and stops at STOP."""
        raw_text = """# Header comment
1950 1.0 2.0
1951 3.0 4.0
STOP
1952 5.0 6.0"""

        lines = fetcher._filter_data_lines(raw_text, skiprows=[])

        assert len(lines) == 2
        assert lines[0] == "1950 1.0 2.0"
        assert lines[1] == "1951 3.0 4.0"

    def test_preprocess_filters_invalid_years(self, fetcher):
        """Test preprocessing filters invalid years."""
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("1950-01-15", periods=5, freq="MS"),
                "value": [1.0, 2.0, 3.0, 4.0, 5.0],
                "year": [1950, 1951, "invalid", 9999, 2024],
            }
        )

        config = {"missing": -99.99}
        df = fetcher._preprocess_data(df, config)

        # Should filter to valid years only
        assert len(df) == 3

    def test_preprocess_handles_missing_values(self, fetcher):
        """Test preprocessing replaces missing values with NaN."""
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("1950-01-15", periods=3, freq="MS"),
                "value": [1.0, -99.99, 3.0],
                "year": [1950, 1950, 1950],
            }
        )

        config = {"missing": -99.99}
        df = fetcher._preprocess_data(df, config)

        # Should drop row with missing value
        assert len(df) == 2
        assert -99.99 not in df["value"].values

    def test_dmi_uses_updated_psl_timeseries_month_url(self, fetcher):
        """DMI should use PSL timeseries/month data endpoint."""
        config = fetcher.get_indicator_config("dmi")
        url = fetcher._build_url(config)
        assert url == "https://psl.noaa.gov/data/timeseries/month/data/dmi.had.long.data"


# Minimal integration test using factory
TestPSLIntegration = create_fetcher_tests(
    fetcher_class=PSLFetcher,
    source_name="psl",
    sample_indicators=["nino34a"],
    sample_data={
        "nino34a": "1950 -1.99 -1.69 -1.42 -1.54 -1.75 -1.50 -1.08 -0.65 -0.53 -0.82 -1.21 -1.38"
    },
)

# Parsing-only tests using factory
TestPSLParsingMinimal = create_parsing_tests(
    fetcher_class=PSLFetcher,
    test_cases=[
        (
            "nino34a",
            "1950 -1.99 -1.69 -1.42 -1.54 -1.75 -1.50 -1.08 -0.65 -0.53 -0.82 -1.21 -1.38\n1951 -1.21 -0.76 -0.50 -0.33 -0.21 -0.06 0.20 0.34 0.38 0.44 0.40 0.28",
            24,
        ),
        ("soi", "1950 1.0 1.5 0.8 0.3 -0.2 -0.5 -0.8 -1.0 -0.7 -0.4 -0.1 0.2", 12),
    ],
)
