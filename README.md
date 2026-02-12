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
  --forecast-output data/forecast_data.parquet
```

Notes:
- `--output` and `--forecast-output` are optional.
- Default workflow is split parquet under `data/`.
- Frontend runtime no longer depends on committed JSON artifacts.

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
    _index.parquet
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
- Forecast index parquet schema:
  `metric`, `issued_date`, `source`, `forecast_id`, `is_historical`

## Frontend Data Flow

Frontend reads parquet directly in browser.

- Development (`npm run dev`):
  - reads from `/data/...` (served by Vite middleware from repo `data/`)
- GitHub Pages production:
  - resolves to `https://raw.githubusercontent.com/<owner>/<repo>/main/data/...`
  - no build-time JSON conversion required

Optional override:

- `VITE_DATA_BASE_URL` to force a custom parquet base URL

## Frontend Run

```bash
cd frontend
npm install
npm run dev
```

Open the shown local Vite URL.

## CI/CD Data Refresh

- `refresh-data.yml`: runs every 5 days and commits only `data/`
- `deploy-pages.yml`: ignores `data/**` pushes, so parquet-only updates do not trigger frontend rebuild
- Frontend reads latest parquet directly, so page data updates without recompiling UI bundle

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
