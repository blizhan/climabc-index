"""Tests for forecast source parsing helpers."""

from unittest.mock import AsyncMock

import pandas as pd
import pytest
import httpx

from climabc.fetchers.forecast import iri as iri_module
from climabc.fetchers.forecast import (
    _resolve_template_params,
    _extract_iri_issue_date,
    _extract_iri_nino34_values,
    _parse_jamstec_dmi_batch,
    _values_to_batch,
)
from climabc.fetchers.forecast.iri import IriForecastFetcher
from climabc.fetchers.forecast.jamstec import JamstecForecastFetcher


def test_iri_config_uses_plumes_json_with_three_recent_batches(config):
    """IRI configuration should target the three latest plumes JSON batches."""
    iri_config = config["sources"]["iri"]
    indicator_config = iri_config["indicators"]["enso_prob"]

    assert iri_config["base_url"] == "https://ensoforecast.iri.columbia.edu"
    assert iri_config["recent_batches"] == 3
    assert iri_config["default"]["format"] == "json"
    assert indicator_config["endpoint_template"] == "/plumes_json/{year}/{month}"
    assert indicator_config["unit"] == "°C"
    assert "url_template" not in indicator_config
    assert "current_url" not in indicator_config
    assert "params" not in indicator_config


def test_extract_iri_total_values_preserves_season_positions():
    """Invalid IRI totals should leave gaps rather than shift later seasons."""
    payload = {
        "averages": {
            "total": [1, 1.1, None, 1.3, -999, 1.5, "1.6", True, float("inf"), 99]
        }
    }

    values = iri_module._extract_iri_total_values(
        payload,
        issue_date=pd.Timestamp("2026-07-20"),
    )

    assert values == [("JJA", 1.0), ("JAS", 1.1), ("SON", 1.3), ("NDJ", 1.5)]


def test_extract_iri_total_values_skips_oversized_integer_without_shifting():
    """An overflowing integer should not prevent later positioned values."""
    payload = {"averages": {"total": [10**10000, 1.2]}}

    values = iri_module._extract_iri_total_values(
        payload,
        issue_date=pd.Timestamp("2026-07-20"),
    )

    assert values == [("JAS", 1.2)]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"averages": None},
        {"averages": {}},
        {"averages": {"total": {}}},
        {"models": {"total": [1.0]}},
    ],
)
def test_extract_iri_total_values_requires_valid_averages_total_list(payload):
    """IRI JSON parsing should require an averages.total list."""
    assert iri_module._extract_iri_total_values(
        payload,
        issue_date=pd.Timestamp("2026-07-20"),
    ) == []


def test_extract_iri_model_table_returns_season_value_pairs():
    """IRI model table parsing should preserve season labels with values."""
    raw_html = """
    <html>
      <body>
        <table id="modelsTable">
          <thead>
            <tr><th colspan="4">IRI Models</th></tr>
            <tr><th>Model</th><th>NDJ</th><th>DJF</th><th>JFM</th></tr>
          </thead>
          <tbody>
            <tr><th>Average</th><td>0.8</td><td>0.9</td><td>1.0</td></tr>
          </tbody>
        </table>
      </body>
    </html>
    """

    values = _extract_iri_nino34_values(raw_html)
    assert values == [("NDJ", 0.8), ("DJF", 0.9), ("JFM", 1.0)]


def test_values_to_batch_uses_season_to_month_mapping():
    """Season tokens should map to correct target months around year boundary."""
    issue_date = pd.Timestamp("2024-11-01")
    values = [("NDJ", 0.8), ("DJF", 0.9), ("JFM", 1.0)]

    batch = _values_to_batch(values, issue_date=issue_date, metric_key="nino34", source_label="iri")

    assert batch is not None
    assert batch["targetDates"] == ["2024-12", "2025-01", "2025-02"]
    assert batch["data"][0]["nino34"] == 0.8


def test_parse_jamstec_batch_uses_release_split_row():
    """JAMSTEC parser should treat all-NaN row as release month boundary."""
    raw_csv = """time,Obs,Mean,ModelA
2024-01-01,0.1,0.2,0.3
2024-02-01,,,
2024-03-01,,0.4,0.5
2024-04-01,,0.6,0.7
"""

    batch = _parse_jamstec_dmi_batch(raw_csv)

    assert batch is not None
    assert batch["issuedDate"] == "2024-02"
    assert batch["targetDates"] == ["2024-03", "2024-04"]
    assert batch["data"] == [{"dmi": 0.4}, {"dmi": 0.6}]


def test_extract_iri_issue_date_from_published_text():
    """IRI issue month should come from the page published timestamp."""
    raw_html = """
    <html><body>
      <div>IRI Technical ENSO Update Published: January 20, 2026</div>
    </body></html>
    """

    issue_date = _extract_iri_issue_date(raw_html)
    assert issue_date == pd.Timestamp("2026-01-01")


def test_resolve_template_params_uses_title_case_month_name():
    """IRI quick-look URL path requires month token like 'May', not 'may'."""
    resolved = _resolve_template_params({"month": "{current_month_eng}"})
    month = resolved["month"]
    assert month[0].isupper()
    assert month[1:].islower()


def test_source_specific_forecast_modules_are_available(config):
    """Forecast fetchers should be importable from source-specific modules."""
    assert IriForecastFetcher(config).source == "iri"
    assert JamstecForecastFetcher(config).source == "jamstec"


@pytest.mark.asyncio
async def test_iri_fetcher_collects_recent_plumes_json_batches(config, mock_respx):
    """IRI fetcher should request recent JSON issue months in descending order."""
    july_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/6"
    june_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/5"
    mock_respx.get(july_url).respond(
        json={
            "averages": {
                "total": [1.0, 1.1, None, 1.3, -999, 1.5, 1.6, 1.7, 1.8, 99.0]
            }
        }
    )
    mock_respx.get(june_url).respond(json={"averages": {"total": [0.5] * 9}})

    async with IriForecastFetcher(config) as fetcher:
        batches = await fetcher.fetch_batches(
            max_batches=2,
            start_issue_date=pd.Timestamp("2026-07-20"),
        )

    assert [batch["issuedDate"] for batch in batches] == ["2026-07", "2026-06"]
    assert batches[0]["targetDates"] == [
        "2026-07",
        "2026-08",
        "2026-10",
        "2026-12",
        "2027-01",
        "2027-02",
        "2027-03",
    ]
    assert [point["nino34"] for point in batches[0]["data"]] == [
        1.0,
        1.1,
        1.3,
        1.5,
        1.6,
        1.7,
        1.8,
    ]
    assert [str(call.request.url) for call in mock_respx.calls] == [july_url, june_url]


@pytest.mark.asyncio
async def test_iri_fetcher_skips_request_and_json_failures(
    config,
    mock_respx,
    caplog,
):
    """One failed issue month should not prevent trying older JSON batches."""
    january_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/0"
    december_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2025/11"
    november_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2025/10"
    mock_respx.get(january_url).mock(side_effect=httpx.ConnectError("connection failed"))
    mock_respx.get(december_url).respond(text="not-json")
    mock_respx.get(november_url).respond(
        json={"averages": {"total": [0.25, 0.3, True, None, -999.0]}}
    )
    caplog.set_level("WARNING", logger="climabc.fetchers.forecast.iri")

    async with IriForecastFetcher(config) as fetcher:
        batches = await fetcher.fetch_batches(
            max_batches=3,
            start_issue_date=pd.Timestamp("2026-01-01 00:30", tz="Asia/Shanghai"),
        )

    assert len(batches) == 1
    assert batches[0]["issuedDate"] == "2025-11"
    assert batches[0]["targetDates"] == ["2025-11", "2025-12"]
    assert batches[0]["data"] == [{"nino34": 0.25}, {"nino34": 0.3}]
    assert [str(call.request.url) for call in mock_respx.calls] == [
        january_url,
        december_url,
        november_url,
    ]
    assert "request failed" in caplog.text
    assert "2026-01" in caplog.text
    assert "invalid JSON" in caplog.text
    assert "2025-12" in caplog.text


@pytest.mark.asyncio
async def test_iri_fetcher_skips_http_and_empty_json_batches(
    config,
    mock_respx,
    caplog,
):
    """HTTP errors and unusable totals should be logged while searching older months."""
    july_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/6"
    june_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/5"
    may_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/4"
    mock_respx.get(july_url).respond(status_code=503)
    mock_respx.get(june_url).respond(
        json={"averages": {"total": [None, -999, "1.0"]}}
    )
    mock_respx.get(may_url).respond(json={"averages": {"total": [0.2]}})
    caplog.set_level("WARNING", logger="climabc.fetchers.forecast.iri")

    async with IriForecastFetcher(config) as fetcher:
        batches = await fetcher.fetch_batches(
            max_batches=3,
            start_issue_date=pd.Timestamp("2026-07-20"),
        )

    assert len(batches) == 1
    assert batches[0]["issuedDate"] == "2026-05"
    assert "HTTP 503" in caplog.text
    assert "2026-07" in caplog.text
    assert "missing usable averages.total" in caplog.text
    assert "2026-06" in caplog.text


@pytest.mark.asyncio
async def test_iri_fetcher_defaults_to_current_month(
    config,
    mock_respx,
    monkeypatch,
):
    """Omitting a start date should request the current calendar month's JSON."""
    july_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/6"
    mock_respx.get(july_url).respond(json={"averages": {"total": [0.4]}})
    monkeypatch.setattr(
        iri_module,
        "_current_month_start",
        lambda: pd.Timestamp("2026-07-01"),
    )

    async with IriForecastFetcher(config) as fetcher:
        batches = await fetcher.fetch_batches(max_batches=1)

    assert batches[0]["issuedDate"] == "2026-07"
    assert [str(call.request.url) for call in mock_respx.calls] == [july_url]


@pytest.mark.asyncio
async def test_iri_fetcher_caps_search_at_three_json_batches_without_fallback(
    config,
    mock_respx,
):
    """Large limits should not expand the JSON search or trigger fallback requests."""
    urls = [
        "https://ensoforecast.iri.columbia.edu/plumes_json/2026/6",
        "https://ensoforecast.iri.columbia.edu/plumes_json/2026/5",
        "https://ensoforecast.iri.columbia.edu/plumes_json/2026/4",
    ]
    for url in urls:
        mock_respx.get(url).respond(json={"models": [{"data": [9.9] * 9}]})

    async with IriForecastFetcher(config) as fetcher:
        batches = await fetcher.fetch_batches(
            max_batches=99,
            start_issue_date=pd.Timestamp("2026-07-01"),
        )

    requested_urls = [str(call.request.url) for call in mock_respx.calls]
    assert batches == []
    assert requested_urls == urls
    assert all("quick-look" not in url and "/current/" not in url for url in requested_urls)


@pytest.mark.asyncio
@pytest.mark.parametrize("max_batches", ["3", 1.5, True, None])
async def test_iri_fetcher_rejects_non_integer_max_batches_before_network_activity(
    config,
    mock_respx,
    max_batches,
):
    """Non-integer limits should fail before any forecast request is made."""
    async with IriForecastFetcher(config) as fetcher:
        with pytest.raises(ValueError, match="max_batches"):
            await fetcher.fetch_batches(max_batches=max_batches)

    assert mock_respx.calls.call_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("max_batches", [0, -2])
async def test_iri_fetcher_normalizes_nonpositive_limits_to_one_successful_batch(
    config,
    mock_respx,
    max_batches,
):
    """Nonpositive limits should continue until one usable batch is collected."""
    july_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/6"
    june_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/5"
    mock_respx.get(july_url).respond(json={"averages": {"total": []}})
    mock_respx.get(june_url).respond(json={"averages": {"total": [0.3]}})

    async with IriForecastFetcher(config) as fetcher:
        batches = await fetcher.fetch_batches(
            max_batches=max_batches,
            start_issue_date=pd.Timestamp("2026-07-01"),
        )

    assert [batch["issuedDate"] for batch in batches] == ["2026-06"]
    assert [str(call.request.url) for call in mock_respx.calls] == [july_url, june_url]


@pytest.mark.asyncio
async def test_iri_fetch_batch_delegates_to_single_batch_fetch(config):
    """The single-batch API should delegate with an explicit one-batch limit."""
    fetcher = IriForecastFetcher(config)
    fetcher.fetch_batches = AsyncMock(return_value=[{"issuedDate": "2026-07"}])
    try:
        batch = await fetcher.fetch_batch()
    finally:
        await fetcher.client.aclose()

    assert batch == {"issuedDate": "2026-07"}
    fetcher.fetch_batches.assert_awaited_once_with(max_batches=1)
