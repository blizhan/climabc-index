"""Regression tests for CLI generate command and frontend data contract."""

import json

import pandas as pd
import pytest
from click.testing import CliRunner

import climabc.cli as cli_module


def _sample_indicator_data() -> dict[str, pd.DataFrame]:
    """Create minimal indicator data for CLI generate tests."""
    ts = pd.Timestamp("2024-01-15")
    return {
        "nino34a": pd.DataFrame({"timestamp": [ts], "value": [1.1]}),
        "nino1a": pd.DataFrame({"timestamp": [ts], "value": [0.2]}),
        "nino3a": pd.DataFrame({"timestamp": [ts], "value": [0.9]}),
        "nino4a": pd.DataFrame({"timestamp": [ts], "value": [0.7]}),
        "soi": pd.DataFrame({"timestamp": [ts], "value": [-4.5]}),
        "oni": pd.DataFrame({"timestamp": [ts], "value": [1.0]}),
        "dmi": pd.DataFrame({"timestamp": [ts], "value": [0.2]}),
    }


def _sample_indicator_data_with_anomalies() -> dict[str, pd.DataFrame]:
    """Create indicator data containing explicit invalid/missing markers."""
    ts1 = pd.Timestamp("2024-01-15")
    ts2 = pd.Timestamp("2024-02-15")
    return {
        "nino34a": pd.DataFrame({"timestamp": [ts1, ts2], "value": [1.1, 1.2]}),
        "nino1a": pd.DataFrame({"timestamp": [ts1, ts2], "value": [0.2, 0.3]}),
        "nino3a": pd.DataFrame({"timestamp": [ts1, ts2], "value": [0.9, 1.0]}),
        "nino4a": pd.DataFrame({"timestamp": [ts1, ts2], "value": [0.7, 0.8]}),
        "soi": pd.DataFrame({"timestamp": [ts1, ts2], "value": [-99.99, -4.5]}),
        "oni": pd.DataFrame({"timestamp": [ts1, ts2], "value": [2025.0, 1.0]}),
        "dmi": pd.DataFrame({"timestamp": [ts1, ts2], "value": [0.2, 0.3]}),
    }


def _sample_indicator_data_with_dmi_trailing_missing() -> dict[str, pd.DataFrame]:
    """Create data where DMI trails but core ENSO indicators remain available."""
    ts1 = pd.Timestamp("2025-04-15")
    ts2 = pd.Timestamp("2025-05-15")
    return {
        "nino34a": pd.DataFrame({"timestamp": [ts1, ts2], "value": [0.1, 0.2]}),
        "nino1a": pd.DataFrame({"timestamp": [ts1, ts2], "value": [0.2, 0.3]}),
        "nino3a": pd.DataFrame({"timestamp": [ts1, ts2], "value": [0.3, 0.4]}),
        "nino4a": pd.DataFrame({"timestamp": [ts1, ts2], "value": [0.4, 0.5]}),
        "soi": pd.DataFrame({"timestamp": [ts1, ts2], "value": [1.2, 1.3]}),
        "oni": pd.DataFrame({"timestamp": [ts1, ts2], "value": [0.0, 0.1]}),
        "dmi": pd.DataFrame({"timestamp": [ts1, ts2], "value": [0.25, -9999.0]}),
    }


def _run_generate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    fake_fetch_all_data,
    fake_fetch_forecast_batches=None,
    with_json_output=False,
    with_merged_parquet_outputs=True,
):
    """Execute CLI generate with mocked data fetch."""
    config_path = tmp_path / "indicators.yaml"
    config_path.write_text("sources: {}\n")

    output_path = tmp_path / "enso_data.parquet"
    forecast_output_path = tmp_path / "forecast_data.parquet"
    json_output = tmp_path / "enso_data.json"
    split_output_dir = tmp_path / "split-data"

    monkeypatch.setattr(cli_module, "fetch_all_data", fake_fetch_all_data)
    if fake_fetch_forecast_batches is None:
        async def fake_fetch_forecast_batches(_config):
            return []

    monkeypatch.setattr(
        cli_module, "fetch_forecast_batches", fake_fetch_forecast_batches
    )

    runner = CliRunner()
    args = [
        "generate",
        "--config",
        str(config_path),
        "--split-output-dir",
        str(split_output_dir),
    ]
    if with_merged_parquet_outputs:
        args.extend(["--output", str(output_path)])
        args.extend(["--forecast-output", str(forecast_output_path)])
    if with_json_output:
        args.extend(["--json-output", str(json_output)])

    result = runner.invoke(
        cli_module.cli,
        args,
    )

    return result, output_path, forecast_output_path, json_output, split_output_dir


def test_generate_passes_frontend_indicator_scope(monkeypatch, tmp_path):
    """generate should fetch only indicators required by frontend."""
    captured: dict[str, object] = {}

    async def fake_fetch_all_data(config, indicators=None):
        captured["indicators"] = indicators
        return _sample_indicator_data()

    result, _, _, _, _ = _run_generate(monkeypatch, tmp_path, fake_fetch_all_data)

    assert result.exit_code == 0, result.output
    assert captured["indicators"] == [
        "nino34a",
        "nino1a",
        "nino3a",
        "nino4a",
        "soi",
        "oni",
        "dmi",
    ]


def test_generate_json_output_is_optional(monkeypatch, tmp_path):
    """generate should not emit JSON unless json output option is provided."""

    async def fake_fetch_all_data(config, indicators=None):
        return _sample_indicator_data()

    result, _, _, json_output, _ = _run_generate(monkeypatch, tmp_path, fake_fetch_all_data)
    assert result.exit_code == 0, result.output
    assert not json_output.exists()


def test_generate_merged_parquet_outputs_are_optional(monkeypatch, tmp_path):
    """generate should not emit merged parquet files unless explicitly requested."""

    async def fake_fetch_all_data(config, indicators=None):
        return _sample_indicator_data()

    result, output_path, forecast_output_path, _, split_output_dir = _run_generate(
        monkeypatch,
        tmp_path,
        fake_fetch_all_data,
        with_merged_parquet_outputs=False,
    )

    assert result.exit_code == 0, result.output
    assert not output_path.exists()
    assert not forecast_output_path.exists()
    assert (split_output_dir / "observations" / "nino34.parquet").exists()


def test_generate_json_includes_nino12_from_nino1a_when_requested(monkeypatch, tmp_path):
    """generate JSON output should include nino12 for frontend compatibility."""

    async def fake_fetch_all_data(config, indicators=None):
        return _sample_indicator_data()

    result, _, _, json_output, _ = _run_generate(
        monkeypatch,
        tmp_path,
        fake_fetch_all_data,
        with_json_output=True,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(json_output.read_text())
    assert payload["observations"]
    assert "nino12" in payload["observations"][0]
    assert payload["observations"][0]["nino12"] == pytest.approx(0.2)


def test_generate_uses_real_forecast_source_not_synthetic(monkeypatch, tmp_path):
    """generate must not call synthetic forecast generation path."""

    async def fake_fetch_all_data(config, indicators=None):
        return _sample_indicator_data()

    async def fake_fetch_forecast_batches(_config):
        return [
            {
                "id": "forecast-iri-2024-01",
                "issuedDate": "2024-01",
                "targetDates": ["2024-02"],
                "data": [{"nino34": 0.8}],
                "isHistorical": True,
            }
        ]

    result, _, forecast_output, json_output, _ = _run_generate(
        monkeypatch,
        tmp_path,
        fake_fetch_all_data,
        fake_fetch_forecast_batches=fake_fetch_forecast_batches,
        with_json_output=True,
    )

    assert result.exit_code == 0, result.output
    forecast_df = pd.read_parquet(forecast_output)
    assert not forecast_df.empty
    assert set(["source", "forecast_id", "issued_date", "target_date", "metric", "value"]).issubset(
        set(forecast_df.columns)
    )
    payload = json.loads(json_output.read_text())
    assert payload["forecasts"]
    assert payload["forecasts"][0]["id"] == "forecast-iri-2024-01"


def test_generate_splits_observation_files_by_metric(monkeypatch, tmp_path):
    """observation data should be split to one file per metric."""

    async def fake_fetch_all_data(config, indicators=None):
        return _sample_indicator_data()

    result, _, _, _, split_output_dir = _run_generate(monkeypatch, tmp_path, fake_fetch_all_data)

    assert result.exit_code == 0, result.output
    obs_dir = split_output_dir / "observations"
    assert (obs_dir / "nino34.parquet").exists()
    assert (obs_dir / "nino12.parquet").exists()
    assert (obs_dir / "soi.parquet").exists()

    nino34_df = pd.read_parquet(obs_dir / "nino34.parquet")
    assert not nino34_df.empty
    assert set(nino34_df.columns) == {"date", "value"}


def test_generate_splits_forecast_files_by_metric_and_batch(monkeypatch, tmp_path):
    """forecast data should be split by metric and forecast batch."""

    async def fake_fetch_all_data(config, indicators=None):
        return _sample_indicator_data()

    async def fake_fetch_forecast_batches(_config):
        return [
            {
                "id": "forecast-iri-2024-01",
                "issuedDate": "2024-01",
                "targetDates": ["2024-02", "2024-03"],
                "data": [{"nino34": 0.8}, {"nino34": 0.9}],
                "isHistorical": True,
            },
            {
                "id": "forecast-iri-2024-02",
                "issuedDate": "2024-02",
                "targetDates": ["2024-03", "2024-04"],
                "data": [{"nino34": 1.0}, {"nino34": 1.1}],
                "isHistorical": True,
            },
        ]

    result, _, _, _, split_output_dir = _run_generate(
        monkeypatch,
        tmp_path,
        fake_fetch_all_data,
        fake_fetch_forecast_batches=fake_fetch_forecast_batches,
    )

    assert result.exit_code == 0, result.output
    forecast_metric_dir = split_output_dir / "forecasts" / "nino34"
    assert (forecast_metric_dir / "2024-01.parquet").exists()
    assert (forecast_metric_dir / "2024-02.parquet").exists()

    batch_df = pd.read_parquet(forecast_metric_dir / "2024-01.parquet")
    assert not batch_df.empty
    assert set(["forecast_id", "source", "issued_date", "metric", "target_date", "value"]).issubset(
        set(batch_df.columns)
    )
    assert batch_df.iloc[0]["issued_date"] == "2024-01"
    assert batch_df.iloc[0]["metric"] == "nino34"
    assert batch_df.iloc[0]["target_date"] == "2024-02"
    assert batch_df.iloc[0]["value"] == pytest.approx(0.8)

    index_path = split_output_dir / "forecasts" / "_index.parquet"
    assert index_path.exists()
    index_df = pd.read_parquet(index_path)
    assert set(["metric", "issued_date", "source", "forecast_id", "is_historical"]).issubset(
        set(index_df.columns)
    )
    assert set(index_df["metric"]) == {"nino34"}




def test_generate_forecast_index_preserves_existing_history(monkeypatch, tmp_path):
    """Existing forecast index entries should be kept when adding new batches."""

    async def fake_fetch_all_data(config, indicators=None):
        return _sample_indicator_data()

    async def fake_fetch_forecast_batches(_config):
        return [
            {
                "id": "forecast-iri-2025-02",
                "issuedDate": "2025-02",
                "targetDates": ["2025-03"],
                "data": [{"nino34": 0.6}],
                "isHistorical": False,
            }
        ]

    split_output_dir = tmp_path / "split-data"
    forecasts_dir = split_output_dir / "forecasts"
    forecasts_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {
                "metric": "nino34",
                "issued_date": "2020-01",
                "source": "iri",
                "forecast_id": "forecast-iri-2020-01",
                "is_historical": True,
            }
        ]
    ).to_parquet(forecasts_dir / "_index.parquet", index=False)

    result, _, _, _, split_output_dir = _run_generate(
        monkeypatch,
        tmp_path,
        fake_fetch_all_data,
        fake_fetch_forecast_batches=fake_fetch_forecast_batches,
    )

    assert result.exit_code == 0, result.output

    index_df = pd.read_parquet(split_output_dir / "forecasts" / "_index.parquet")
    assert len(index_df) == 2
    assert set(index_df["issued_date"]) == {"2020-01", "2025-02"}

def test_generate_replaces_detected_anomalies_before_parquet(monkeypatch, tmp_path):
    """Detected invalid values must be converted to NaN before parquet save."""

    async def fake_fetch_all_data(config, indicators=None):
        return _sample_indicator_data_with_anomalies()

    result, output_path, _, _, _ = _run_generate(monkeypatch, tmp_path, fake_fetch_all_data)

    assert result.exit_code == 0, result.output
    df = pd.read_parquet(output_path)
    assert not df.empty
    assert (df["soi"] == -99.99).sum() == 0
    assert (df["oni"] == 2025.0).sum() == 0
    assert len(df) == 2
    assert df["soi"].isna().sum() == 1
    assert df["oni"].isna().sum() == 1


def test_generate_keeps_recent_rows_when_dmi_is_missing(monkeypatch, tmp_path):
    """Rows with core ENSO data should remain even when DMI is missing."""

    async def fake_fetch_all_data(config, indicators=None):
        return _sample_indicator_data_with_dmi_trailing_missing()

    result, output_path, _, _, split_output_dir = _run_generate(
        monkeypatch,
        tmp_path,
        fake_fetch_all_data,
        with_merged_parquet_outputs=True,
    )

    assert result.exit_code == 0, result.output
    merged_df = pd.read_parquet(output_path)
    assert list(merged_df["date"]) == ["2025-04", "2025-05"]
    assert merged_df["dmi"].isna().sum() == 1

    dmi_df = pd.read_parquet(split_output_dir / "observations" / "dmi.parquet")
    assert list(dmi_df["date"]) == ["2025-04"]

    nino34_df = pd.read_parquet(split_output_dir / "observations" / "nino34.parquet")
    assert list(nino34_df["date"]) == ["2025-04", "2025-05"]
