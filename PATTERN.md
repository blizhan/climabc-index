# ClimABC Delivery Pattern (Current)

This document describes the *current working pattern used in this repository*.
It is intentionally practical and implementation-oriented.

## 1. Core Principles

- Source-specific fetchers, shared base behavior.
- Configuration-driven source metadata (`indicators.yaml`).
- No synthetic data in production data refresh.
- Split parquet as canonical persisted dataset format.
- Frontend behavior follows data contract, not ad-hoc JSON structures.

## 2. Runtime Architecture

### Observation path

- Main source for current UI contract: PSL indicators.
- Fetcher: `PSLFetcher` (under `src/climabc/fetchers/`).
- Output is normalized and sanitized before persistence.

### Forecast path

Forecast fetchers are modularized under:

- `src/climabc/fetchers/forecast/iri.py`
- `src/climabc/fetchers/forecast/jamstec.py`

Key behavior:
- IRI: fetch latest `current` page first, then backfill historical monthly quick-look pages.
- JAMSTEC: parse release split row in SINTEX DMI CSV and produce forecast batch.

## 3. Data Contract

Canonical output (default `generate` behavior):

```text
data/
  observations/
    <metric>.parquet
  forecasts/
    _index.parquet
    <metric>/
      <issued_month>.parquet
```

Schemas:

- Observation parquet:
  - `date`, `value`
- Forecast parquet:
  - `forecast_id`, `source`, `issued_date`, `target_date`, `metric`, `value`, `is_historical`
- Forecast index parquet:
  - `metric`, `issued_date`, `source`, `forecast_id`, `is_historical`

## 4. CLI Contract

Primary command:

```bash
uv run climabc generate --split-output-dir data
```

Expected responsibilities:
- fetch configured real sources
- merge/normalize required observation indicators
- replace known missing markers and detected outliers with `NaN` before parquet write
- persist split parquet datasets

Optional outputs are compatibility/debug features, not the primary contract.

## 5. Frontend Data Pattern

Data loader behavior:
- Development: read `/data/...` parquet files served by Vite middleware.
- Production (GitHub Pages): read parquet files from raw GitHub URL (`main/data`).
- Optional override: `VITE_DATA_BASE_URL`.

Runtime assembly:
- Frontend loads observation parquet by metric.
- Frontend reads `forecasts/_index.parquet` to discover `(metric, issued_date)` files.
- Frontend merges batch parquet rows into monthly forecast batches.

## 6. CI/CD Pattern

### Data refresh workflow

- Scheduled every 5 days.
- Runs CLI generate.
- Commits only `data/` changes to `main`.

### Pages deploy workflow

- Triggered on `main` push while ignoring `data/**` changes.
- Builds frontend and deploys `frontend/dist` to GitHub Pages.
- Data-only refresh commits do not trigger UI rebuild; frontend reads latest parquet at runtime.

## 7. Testing Pattern

- Unit tests for fetcher parsing and adapter conversion.
- CLI regression tests for:
  - indicator scope
  - split parquet output
  - anomaly sanitization
  - forecast flattening/splitting behavior
- Frontend utility tests for forecast metadata and timeline behavior.

## 8. Extension Rules

When adding a new source:
- add config in `indicators.yaml`
- implement source fetcher in matching module tree
- map data to existing frontend metric keys or explicitly extend metric contract
- add regression tests for parsing and output layout
- keep split parquet contract stable unless versioned migration is introduced

This pattern is the repository baseline unless replaced by a newer, explicit version.
