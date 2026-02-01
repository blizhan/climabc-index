"""Tests for NCEI fetcher."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pytest
from utils import create_fetcher_tests, create_parsing_tests

from climabc.fetchers import NCEIFetcher


class TestNCEIParsing:
    """Test NCEI-specific parsing logic."""

    @pytest.fixture
    def fetcher(self, config):
        return NCEIFetcher(config)

    def test_parse_monthly_multi_column_format(self, fetcher):
        raw_text = """1950 1 1.0 2.0 3.0 4.0
1950 2 1.1 2.1 3.1 4.1"""
        config = fetcher.get_indicator_config("nina_all")

        df = fetcher._parse_data(raw_text, config)
        df = fetcher._preprocess_data(df, config)

        assert len(df) == 8
        assert set(df["indicator"].unique()) == {
            "nina3a",
            "nina4a",
            "nina34a",
            "nina12a",
        }

    def test_parse_monthly_single_column_format(self, fetcher):
        raw_text = """Header line 1
Header line 2
1950 1 0.1
1950 2 0.2"""
        config = fetcher.get_indicator_config("amo")

        df = fetcher._parse_data(raw_text, config)
        df = fetcher._preprocess_data(df, config)

        assert len(df) == 2
        assert "indicator" not in df.columns

    def test_parse_wide_format(self, fetcher):
        raw_text = "1950 1.0 2.0 3.0 4.0 5.0 6.0 7.0 8.0 9.0 10.0 11.0 12.0"
        config = fetcher.get_indicator_config("pdo")

        df = fetcher._parse_data(raw_text, config)
        df = fetcher._preprocess_data(df, config)

        assert len(df) == 12

    def test_preprocess_handles_missing_values(self, fetcher):
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("1950-01-15", periods=3, freq="MS"),
                "value": [1.0, 99.99, 3.0],
                "year": [1950, 1950, 1950],
            }
        )
        config = {"missing": 99.99}
        df = fetcher._preprocess_data(df, config)

        assert len(df) == 2
        assert 99.99 not in df["value"].values


# Minimal integration tests using factory
TestNCEIIntegration = create_fetcher_tests(
    fetcher_class=NCEIFetcher,
    source_name="ncei",
    sample_indicators=["amo"],
    sample_data={"amo": "1950 1 0.1\n1950 2 0.2"},
)

# Parsing-only tests using factory
TestNCEIParsingMinimal = create_parsing_tests(
    fetcher_class=NCEIFetcher,
    test_cases=[
        ("pdo", "1950 1 2 3 4 5 6 7 8 9 10 11 12", 12),
        ("amo", "1950 1 0.1\n1950 2 0.2", 2),
    ],
)
