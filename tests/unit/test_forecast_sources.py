"""Tests for forecast source parsing helpers."""

from copy import deepcopy

import pandas as pd
import pytest

from climabc.fetchers.forecast import (
    _resolve_template_params,
    _extract_iri_issue_date,
    _extract_iri_nino34_values,
    _parse_jamstec_dmi_batch,
    _values_to_batch,
)
from climabc.fetchers.forecast.iri import IriForecastFetcher
from climabc.fetchers.forecast.jamstec import JamstecForecastFetcher


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
async def test_iri_fetcher_can_collect_recent_multiple_batches(config, mock_respx):
    """IRI fetcher should collect multiple recent monthly batches."""
    cfg = deepcopy(config)
    cfg["sources"]["jamstec"]["type"] = "observation"

    dec_url = (
        "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/"
        "2025-December-quick-look/?enso_tab=enso-sst_table"
    )
    nov_url = (
        "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/"
        "2025-November-quick-look/?enso_tab=enso-sst_table"
    )

    dec_html = """
    <html><body>
      <div>Published: December 18, 2025</div>
      <table id="modelsTable">
        <thead>
          <tr><th colspan="4">IRI Models</th></tr>
          <tr><th>Model</th><th>NDJ</th><th>DJF</th><th>JFM</th></tr>
        </thead>
        <tbody>
          <tr><th>Average</th><td>0.8</td><td>0.9</td><td>1.0</td></tr>
        </tbody>
      </table>
    </body></html>
    """
    nov_html = """
    <html><body>
      <div>Published: November 17, 2025</div>
      <table id="modelsTable">
        <thead>
          <tr><th colspan="4">IRI Models</th></tr>
          <tr><th>Model</th><th>OND</th><th>NDJ</th><th>DJF</th></tr>
        </thead>
        <tbody>
          <tr><th>Average</th><td>0.6</td><td>0.7</td><td>0.8</td></tr>
        </tbody>
      </table>
    </body></html>
    """

    mock_respx.get(dec_url).respond(status_code=200, text=dec_html)
    mock_respx.get(nov_url).respond(status_code=200, text=nov_html)
    mock_respx.get(
        "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/"
        "2025-October-quick-look/?enso_tab=enso-sst_table"
    ).respond(status_code=404, text="")

    async with IriForecastFetcher(cfg) as fetcher:
        batches = await fetcher.fetch_batches(
            max_batches=2,
            start_issue_date=pd.Timestamp("2025-12-01"),
        )

    assert len(batches) == 2
    assert batches[0]["issuedDate"] == "2025-12"
    assert batches[1]["issuedDate"] == "2025-11"


@pytest.mark.asyncio
async def test_iri_fetcher_includes_current_batch_and_history(config, mock_respx):
    """IRI fetcher should load latest `current` batch and then backfill history."""
    cfg = deepcopy(config)
    cfg["sources"]["jamstec"]["type"] = "observation"

    current_url = (
        "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/"
        "current/?enso_tab=enso-sst_table"
    )
    dec_url = (
        "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/"
        "2025-December-quick-look/?enso_tab=enso-sst_table"
    )
    nov_url = (
        "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/"
        "2025-November-quick-look/?enso_tab=enso-sst_table"
    )

    current_html = """
    <html><body>
      <div>Published: January 20, 2026</div>
      <table id="modelsTable">
        <thead>
          <tr><th colspan="4">IRI Models</th></tr>
          <tr><th>Model</th><th>JFM</th><th>FMA</th><th>MAM</th></tr>
        </thead>
        <tbody>
          <tr><th>Average</th><td>1.2</td><td>1.1</td><td>1.0</td></tr>
        </tbody>
      </table>
    </body></html>
    """
    dec_html = """
    <html><body>
      <div>Published: December 18, 2025</div>
      <table id="modelsTable">
        <thead>
          <tr><th colspan="4">IRI Models</th></tr>
          <tr><th>Model</th><th>NDJ</th><th>DJF</th><th>JFM</th></tr>
        </thead>
        <tbody>
          <tr><th>Average</th><td>0.8</td><td>0.9</td><td>1.0</td></tr>
        </tbody>
      </table>
    </body></html>
    """
    nov_html = """
    <html><body>
      <div>Published: November 17, 2025</div>
      <table id="modelsTable">
        <thead>
          <tr><th colspan="4">IRI Models</th></tr>
          <tr><th>Model</th><th>OND</th><th>NDJ</th><th>DJF</th></tr>
        </thead>
        <tbody>
          <tr><th>Average</th><td>0.6</td><td>0.7</td><td>0.8</td></tr>
        </tbody>
      </table>
    </body></html>
    """

    mock_respx.get(current_url).respond(status_code=200, text=current_html)
    mock_respx.get(dec_url).respond(status_code=200, text=dec_html)
    mock_respx.get(nov_url).respond(status_code=200, text=nov_html)

    mock_respx.get(
        "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/"
        "2026-February-quick-look/?enso_tab=enso-sst_table"
    ).respond(status_code=404, text="")
    mock_respx.get(
        "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/"
        "2026-January-quick-look/?enso_tab=enso-sst_table"
    ).respond(status_code=404, text="")
    mock_respx.get(
        "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/"
        "2025-October-quick-look/?enso_tab=enso-sst_table"
    ).respond(status_code=404, text="")

    async with IriForecastFetcher(cfg) as fetcher:
        batches = await fetcher.fetch_batches(
            max_batches=3,
            start_issue_date=pd.Timestamp("2026-02-01"),
        )

    assert len(batches) == 3
    assert [batch["issuedDate"] for batch in batches] == ["2026-01", "2025-12", "2025-11"]
