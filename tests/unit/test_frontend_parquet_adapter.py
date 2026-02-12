"""Tests for frontend parquet adapter script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_frontend_adapter_reads_observation_and_forecasts_directories(tmp_path):
    """Adapter should build frontend payload from data/observations and data/forecasts."""
    observation_dir = tmp_path / "data" / "observations"
    forecasts_dir = tmp_path / "data" / "forecasts"
    observation_dir.mkdir(parents=True, exist_ok=True)
    (forecasts_dir / "nino34").mkdir(parents=True, exist_ok=True)
    (forecasts_dir / "dmi").mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {"date": "2025-10", "value": 0.1},
            {"date": "2025-11", "value": 0.2},
        ]
    ).to_parquet(observation_dir / "nino34.parquet", index=False)
    pd.DataFrame(
        [
            {"date": "2025-10", "value": 1.0},
            {"date": "2025-11", "value": 0.8},
        ]
    ).to_parquet(observation_dir / "soi.parquet", index=False)

    pd.DataFrame(
        [
            {
                "forecast_id": "forecast-iri-2025-10",
                "source": "iri",
                "issued_date": "2025-10",
                "target_date": "2025-11",
                "metric": "nino34",
                "value": 0.3,
                "is_historical": False,
            }
        ]
    ).to_parquet(forecasts_dir / "nino34" / "2025-10.parquet", index=False)
    pd.DataFrame(
        [
            {
                "forecast_id": "forecast-jamstec-2025-10",
                "source": "jamstec",
                "issued_date": "2025-10",
                "target_date": "2025-11",
                "metric": "dmi",
                "value": 0.4,
                "is_historical": False,
            }
        ]
    ).to_parquet(forecasts_dir / "dmi" / "2025-10.parquet", index=False)

    script_path = Path(__file__).resolve().parents[2] / "frontend" / "scripts" / "parquet_to_frontend_json.py"
    raw_output = subprocess.check_output(
        [sys.executable, str(script_path), str(observation_dir), str(forecasts_dir)],
        text=True,
    )
    payload = json.loads(raw_output)

    assert payload["observations"]
    assert "nino34" in payload["observations"][0]
    assert "soi" in payload["observations"][0]

    forecast_ids = {item["id"] for item in payload["forecasts"]}
    assert "forecast-iri-2025-10" in forecast_ids
    assert "forecast-jamstec-2025-10" in forecast_ids
