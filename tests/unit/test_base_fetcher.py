"""Tests for BaseFetcher utility methods."""

import numpy as np
import pandas as pd
import pytest

from climabc.fetchers.base import BaseFetcher


class TestIsValidYear:
    """Tests for BaseFetcher._is_valid_year method."""

    @pytest.mark.parametrize(
        "year_str,expected",
        [
            ("1950", True),
            ("2024", True),
            ("1", True),
            ("2200", True),
            ("0", False),
            ("2201", False),
            ("abc", False),
            ("", False),
            (None, False),
            (1950, True),
            (1950.0, True),
        ],
    )
    def test_year_validation(self, year_str, expected):
        assert BaseFetcher._is_valid_year(year_str) == expected


class TestReplaceMissingWithNan:
    """Tests for BaseFetcher._replace_missing_with_nan method."""

    def test_replace_missing_values(self):
        df = pd.DataFrame({"year": [1950, 1951, 1952], "value": [1.0, -99.99, 2.0]})

        result = BaseFetcher._replace_missing_with_nan(df, -99.99)

        assert pd.isna(result.loc[1, "value"])
        assert result.loc[0, "value"] == 1.0
        assert result.loc[2, "value"] == 2.0

    def test_no_missing_value(self):
        df = pd.DataFrame({"year": [1950, 1951], "value": [1.0, 2.0]})

        result = BaseFetcher._replace_missing_with_nan(df, -99.99)

        assert len(result) == 2
        assert not result["value"].isna().any()

    def test_none_missing_value(self):
        df = pd.DataFrame({"year": [1950, 1951], "value": [1.0, 2.0]})

        result = BaseFetcher._replace_missing_with_nan(df, None)

        pd.testing.assert_frame_equal(result, df)


class TestWideToLongTransform:
    """Tests for BaseFetcher._wide_to_long_transform method."""

    def test_basic_transform(self):
        df = pd.DataFrame(
            {"year": [1950, 1951], "1": [1.0, 2.0], "2": [3.0, 4.0], "12": [5.0, 6.0]}
        )

        result = BaseFetcher._wide_to_long_transform(df, id_col="year")

        assert "timestamp" in result.columns
        assert "value" in result.columns
        assert len(result) == 6

        first_row = result.iloc[0]
        assert first_row["timestamp"] == pd.Timestamp("1950-01-15")
        assert first_row["value"] == 1.0

    def test_month_name_columns(self):
        df = pd.DataFrame({"year": [1950], "Jan": [1.0], "Feb": [2.0], "Mar": [3.0]})

        result = BaseFetcher._wide_to_long_transform(df, id_col="year")

        assert len(result) == 3
        assert result.iloc[0]["timestamp"].month == 1
        assert result.iloc[1]["timestamp"].month == 2
        assert result.iloc[2]["timestamp"].month == 3

    def test_drops_nan_values(self):
        df = pd.DataFrame({"year": [1950], "1": [1.0], "2": [np.nan], "3": [3.0]})

        result = BaseFetcher._wide_to_long_transform(df, id_col="year")

        assert len(result) == 2
        assert not result["value"].isna().any()

    def test_sorted_by_date(self):
        df = pd.DataFrame({"year": [1951, 1950], "1": [2.0, 1.0], "2": [4.0, 3.0]})

        result = BaseFetcher._wide_to_long_transform(df, id_col="year")

        timestamps = result["timestamp"].tolist()
        assert timestamps == sorted(timestamps)
