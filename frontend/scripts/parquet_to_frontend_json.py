#!/usr/bin/env python3
"""Convert observation/forecast parquet files into frontend dataset JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


def _clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return value


def _load_observations(observation_path: Path) -> list[dict[str, Any]]:
    if not observation_path.exists():
        return []

    if observation_path.is_file():
        df = pd.read_parquet(observation_path)
        if "date" in df.columns:
            df["date"] = df["date"].astype(str)
        return [{key: _clean_value(val) for key, val in row.items()} for row in df.to_dict("records")]

    metric_frames: list[pd.DataFrame] = []
    for parquet_file in sorted(observation_path.glob("*.parquet")):
        df = pd.read_parquet(parquet_file)
        if df.empty or "date" not in df.columns:
            continue

        metric = parquet_file.stem
        value_column = metric if metric in df.columns else ("value" if "value" in df.columns else None)
        if value_column is None:
            continue

        metric_df = df[["date", value_column]].copy()
        metric_df = metric_df.rename(columns={value_column: metric})
        metric_df["date"] = metric_df["date"].astype(str)
        metric_df[metric] = pd.to_numeric(metric_df[metric], errors="coerce")
        metric_frames.append(metric_df)

    if not metric_frames:
        return []

    df = metric_frames[0]
    for metric_df in metric_frames[1:]:
        df = df.merge(metric_df, on="date", how="outer")

    df = df.sort_values("date").reset_index(drop=True)
    if "date" in df.columns:
        df["date"] = df["date"].astype(str)
    return [{key: _clean_value(val) for key, val in row.items()} for row in df.to_dict("records")]


def _infer_source_from_id(forecast_id: str) -> str:
    token = forecast_id.lower()
    if "jamstec" in token:
        return "jamstec"
    if "iri" in token:
        return "iri"
    return "unknown"


def _load_forecasts(forecast_path: Path) -> list[dict[str, Any]]:
    if not forecast_path.exists():
        return []

    if forecast_path.is_file():
        df = pd.read_parquet(forecast_path)
    else:
        forecast_frames = [
            pd.read_parquet(parquet_file)
            for parquet_file in sorted(forecast_path.rglob("*.parquet"))
        ]
        if not forecast_frames:
            return []
        df = pd.concat(forecast_frames, ignore_index=True, sort=False)

    if df.empty:
        return []

    required_columns = {"forecast_id", "issued_date", "target_date", "metric", "value"}
    if not required_columns.issubset(df.columns):
        return []

    if "source" not in df.columns:
        df["source"] = df["forecast_id"].astype(str).map(_infer_source_from_id)
    if "is_historical" not in df.columns:
        df["is_historical"] = False

    df["forecast_id"] = df["forecast_id"].astype(str)
    df["source"] = df["source"].astype(str)
    df["issued_date"] = df["issued_date"].astype(str)
    df["target_date"] = df["target_date"].astype(str)
    df["metric"] = df["metric"].astype(str)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])

    if df.empty:
        return []

    batches: list[dict[str, Any]] = []
    grouped = df.groupby(["forecast_id", "source", "issued_date", "is_historical"], sort=False, dropna=False)
    for (forecast_id, source, issued_date, is_historical), batch_df in grouped:
        target_dates: list[str] = []
        data_points: list[dict[str, float]] = []

        for target_date, target_df in batch_df.groupby("target_date", sort=True):
            point: dict[str, float] = {}
            for _, row in target_df.sort_values("metric").iterrows():
                point[str(row["metric"])] = float(row["value"])
            if point:
                target_dates.append(str(target_date))
                data_points.append(point)

        if not target_dates:
            continue

        batches.append(
            {
                "id": str(forecast_id),
                "source": str(source),
                "issuedDate": str(issued_date),
                "targetDates": target_dates,
                "data": data_points,
                "isHistorical": bool(is_historical),
            }
        )

    batches.sort(key=lambda item: item.get("issuedDate", ""), reverse=True)
    return batches


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: parquet_to_frontend_json.py <observations-path> <forecasts-path>"
        )

    observation_path = Path(sys.argv[1])
    forecast_path = Path(sys.argv[2])

    observations = _load_observations(observation_path)
    forecasts = _load_forecasts(forecast_path)

    payload = {
        "observations": observations,
        "forecasts": forecasts,
        "latestForecast": forecasts[0] if forecasts else None,
        "selectedForecast": None,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
