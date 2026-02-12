# ClimABC Index

Climate index data pipeline and visualization console for observations and forecasts.

## Current Scope

- Historical observations from **NOAA PSL** (used by CLI generate flow)
- Forecast sources:
  - **IRI ENSO Quick Look** (latest `current` + historical monthly quick-look pages)
  - **JAMSTEC SINTEX-F DMI**
- Frontend timeline and snapshot table reading data from split parquet directories

## Data Sources

| Institution | Type | Indicators in Current UI/Data Contract |
|---|---|---|
| NOAA PSL | Observation | `nino34`, `nino12`, `nino3`, `nino4`, `soi`, `oni`, `dmi` |
| IRI | Forecast | `nino34` |
| JAMSTEC | Forecast | `dmi` |

## Installation

```bash
uv sync
```

## CLI

Entry point:

```bash
uv run climabc --help
```

### 1) Generate real data

```bash
uv run climabc generate \
  --split-output-dir data
```

This command will:
- fetch required PSL observation indicators for frontend
- sanitize known missing markers and out-of-range anomalies to `NaN` before parquet write
- fetch forecast batches from configured forecast sources (IRI + JAMSTEC)
- write split parquet outputs for frontend/backend consumption

Optional outputs:

```bash
uv run climabc generate \
  --split-output-dir data \
  --output data/enso_data.parquet \
  --forecast-output data/forecast_data.parquet \
  --json-output frontend/public/enso_data.json
```

Notes:
- `--output`, `--forecast-output`, and `--json-output` are optional.
- Default workflow is split parquet under `data/`.
- JSON export exists for compatibility/debug only.

### 2) Generate mock data (dev only)

```bash
uv run climabc mock --output-dir frontend/public
```

`mock` creates synthetic data; `generate` uses real sources.

## Output Layout

By default (`--split-output-dir data`):

```text
data/
  observations/
    nino34.parquet
    nino12.parquet
    nino3.parquet
    nino4.parquet
    soi.parquet
    oni.parquet
    dmi.parquet
  forecasts/
    nino34/
      2026-01.parquet
      2025-12.parquet
      ...
    dmi/
      2026-01.parquet
      ...
```

- Observation parquet schema (per metric): `date`, `value`
- Forecast parquet schema (per metric + issue batch):
  `forecast_id`, `source`, `issued_date`, `target_date`, `metric`, `value`, `is_historical`

## Frontend Data Flow

Frontend reads from `/api/enso-data` (Vite middleware), which is built from parquet via:

- `frontend/scripts/parquet_to_frontend_json.py`
- observation input path default: `data/observations`
- forecast input path default: `data/forecasts`

Override paths with env vars:

- `CLIMABC_OBSERVATIONS_PATH` (or legacy `CLIMABC_OBS_PARQUET`)
- `CLIMABC_FORECASTS_PATH` (or legacy `CLIMABC_FORECAST_PARQUET`)

## Frontend Run

```bash
cd frontend
npm install
npm run dev
```

Open the shown local Vite URL.

## Forecast Fetching Behavior

- IRI fetcher first loads:
  - `/our-expertise/climate/forecasts/enso/current/?enso_tab=enso-sst_table`
- Then backfills historical quick-look pages:
  - `/our-expertise/climate/forecasts/enso/{year}-{month}-quick-look/?enso_tab=enso-sst_table`
- JAMSTEC fetcher parses release split from `SINTEX_DMI.csv` and emits DMI forecast batch.

## Tests

```bash
uv run pytest
cd frontend && npm test -- --run
```

## Acknowledgments

Data providers:
- NOAA PSL: https://psl.noaa.gov
- IRI ENSO Quick Look: https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/?enso_tab=enso-sst_table
- JAMSTEC SINTEX-F DMI: https://www.jamstec.go.jp/virtualearth/data/SINTEX/SINTEX_DMI.csv
