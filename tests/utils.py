"""Test utilities for fetcher testing with template method pattern."""

from typing import Dict, Type

import pandas as pd
import pytest

from climabc.fetchers.base import BaseFetcher


class FetcherTestBase:
    """Base class for fetcher tests using template method pattern.

    Subclasses define:
    - fetcher_class: The fetcher class to test
    - source_name: Expected source identifier
    - sample_indicators: List of indicators to test
    - sample_data: Dict mapping indicator -> raw data string
    """

    fetcher_class: Type[BaseFetcher] = None
    source_name: str = None
    sample_indicators: list = []
    sample_data: Dict[str, str] = {}

    @pytest.fixture
    def fetcher(self, config):
        return self.fetcher_class(config)

    def test_source_property(self, fetcher):
        assert fetcher.source == self.source_name

    def test_has_indicators(self, fetcher):
        assert len(fetcher.indicators) > 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("indicator", sample_indicators)
    async def test_fetch_workflow(self, fetcher, mock_respx, indicator):
        if indicator not in self.sample_data:
            pytest.skip(f"No sample data for {indicator}")

        config = fetcher.get_indicator_config(indicator)
        url = fetcher._build_url(config)
        mock_respx.get(url).respond(text=self.sample_data[indicator])

        df = await fetcher.fetch(indicator)

        # Base validation - all fetchers should produce this
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert df["source"].iloc[0] == self.source_name
        assert df["indicator"].iloc[0] == indicator


def create_fetcher_tests(
    fetcher_class: Type[BaseFetcher],
    source_name: str,
    sample_indicators: list,
    sample_data: Dict[str, str],
):
    """Create test class with minimal boilerplate.

    Usage:
        TestNewFetcher = create_fetcher_tests(
            fetcher_class=NewFetcher,
            source_name='new_source',
            sample_indicators=['ind1', 'ind2'],
            sample_data={'ind1': 'raw data...', 'ind2': 'raw data...'}
        )
    """
    attrs = {
        "fetcher_class": fetcher_class,
        "source_name": source_name,
        "sample_indicators": sample_indicators,
        "sample_data": sample_data,
    }
    return type(f"Test{fetcher_class.__name__}", (FetcherTestBase,), attrs)


# New: Test only the specific parsing logic
class FetcherParsingTestBase:
    """Base for testing only the parsing logic (no HTTP)."""

    fetcher_class: Type[BaseFetcher] = None
    test_cases: list = []  # [(indicator, raw_data, expected_records), ...]

    @pytest.fixture
    def fetcher(self, config):
        return self.fetcher_class(config)

    @pytest.mark.parametrize("indicator,raw_data,expected_count", test_cases)
    def test_parse_data(self, fetcher, indicator, raw_data, expected_count):
        config = fetcher.get_indicator_config(indicator)

        df = fetcher._parse_data(raw_data, config)
        df = fetcher._preprocess_data(df, config)

        assert len(df) == expected_count
        assert "timestamp" in df.columns
        assert "value" in df.columns


def create_parsing_tests(fetcher_class, test_cases):
    """Create parsing-only test class.

    Usage:
        TestNewFetcherParsing = create_parsing_tests(
            fetcher_class=NewFetcher,
            test_cases=[
                ('ind1', 'raw data', 12),
                ('ind2', 'raw data', 12),
            ]
        )
    """
    attrs = {
        "fetcher_class": fetcher_class,
        "test_cases": test_cases,
    }
    return type(
        f"Test{fetcher_class.__name__}Parsing", (FetcherParsingTestBase,), attrs
    )
