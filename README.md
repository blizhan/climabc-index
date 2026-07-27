# ClimABC Index

Climate index data pipeline and visualization console for observations and forecasts.
Live Console: https://blizhan.github.io/climabc-index/

## Current Scope

- Historical observations from **NOAA PSL** (used by CLI generate flow)
- Forecast sources:
  - **IRI ENSO forecast plume** (`plumes_json` multi-model mean)
  - **JAMSTEC SINTEX-F DMI**
- Frontend timeline and snapshot table reading data from split parquet directories

## Data Sources

| Institution | Type | Indicators in Current UI/Data Contract |
|---|---|---|
| NOAA PSL | Observation | `nino34`, `nino12`, `nino3`, `nino4`, `soi`, `oni`, `dmi`, `tni`, `censo`, `ao`, `pdo`, `wp`, `amo_us`, `amo_sm`, `dmiwest`, `dmieast`, `nao`, `np`, `tpi`, `glbts`, `glbtssst` |
| IRI | Forecast | `nino34` |
| JAMSTEC | Forecast | `dmi` |

## Index Reference (Repo Mapping)

| Institution | Source | DataType | DataName | FetchData (this repo) |
|---|---|---|---|---|
| IRI | IRI | forecast | Niño 3.4 SST Anomaly | `uv run climabc generate --split-output-dir data` → `src/climabc/fetchers/forecast/iri.py` |
| IRI | CPC | forecast | ENSO Probability | `Not implemented yet` (no CPC forecast fetcher wired) |
| JAMSTEC | JAMSTEC | forecast | Dipole Mode Index | `uv run climabc generate --split-output-dir data` → `src/climabc/fetchers/forecast/jamstec.py` |
| PSL/NCEI | PSL/NCEI | history | Nina 34 Anomaly | `PSL:nino34a` or `NCEI:nina_all.nina34a` |
| PSL/NCEI | PSL/NCEI | history | Nina 3 Anomaly | `PSL:nino3a` or `NCEI:nina_all.nina3a` |
| PSL/NCEI | PSL/NCEI | history | Nina 4 Anomaly | `PSL:nino4a` or `NCEI:nina_all.nina4a` |
| PSL | PSL | history | Nina 1 Anomaly | `PSL:nino1a` |
| NCEI | NCEI | history | Nina 1.2 Anomaly | `NCEI:nina_all.nina12a` |
| NCEI | NCEI | history | Nina 1.2 SST | `NCEI:nina_sst.nina12` |
| NCEI | NCEI | history | Nina 3 SST | `NCEI:nina_sst.nina3` |
| NCEI | NCEI | history | Nina 3.4 SST | `NCEI:nina_sst.nina34` |
| NCEI | NCEI | history | Nina 4 SST | `NCEI:nina_sst.nina4` |
| NCEI | NCEI | history | Indian Ocean Dipole | `NCEI:iod` (`iod_west`, `iod_east`, `iod_diff`) |
| PSL | PSL | history | Southern Oscillation Index | `PSL:soi` |
| PSL | PSL | history | Oceanic Nino index | `PSL:oni` |
| PSL | PSL | history | Trans Nino index | `PSL:tni` |
| PSL | PSL | history | Arctic Oscillation | `PSL:ao` |
| PSL | PSL | history | Bivariate ENSO from nina3.4 & soi | `PSL:censo` |
| PSL | PSL | history | Western Pacific Index | `PSL:wp` |
| PSL | PSL | history | AMO smoothed | `PSL:amo_sm` |
| PSL | PSL | history | Dipole Mode Index | `PSL:dmi` |
| PSL | PSL | history | Dipole Mode Index West | `PSL:dmiwest` |
| PSL | PSL | history | Dipole Mode Index East | `PSL:dmieast` |
| PSL | PSL | history | North Atlantic Oscillation | `PSL:nao` |
| PSL | PSL | history | North Pacific Index | `PSL:np` |
| PSL | PSL | history | Trans Polar Index | `PSL:tpi` |
| PSL | PSL | history | Global Average Temperature Anomaly from Station | `PSL:glbts` |
| PSL | PSL | history | Global Average Temperature Anomaly from Station and SST | `PSL:glbtssst` |
| PSL/NCEI | PSL/NCEI | history | AMO unsmoothed | `NCEI:amo` (also `PSL:amo_us`) |
| PSL/NCEI | PSL/NCEI | history | Pacific Decadal Oscillation | `NCEI:pdo` (also `PSL:pdo`) |

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
- fetch PSL observation indicators declared in config
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

## Output Layout

By default (`--split-output-dir data`):

```text
data/
  observations/
    nino34.parquet
    nino12.parquet
    ...
    glbtssst.parquet
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
  - UI: `https://blizhan.github.io/climabc-index/`
  - parquet base: `https://raw.githubusercontent.com/blizhan/climabc-index/main/data/...`
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

- IRI fetcher requests the Interactive Chart JSON endpoint:
  - `https://ensoforecast.iri.columbia.edu/plumes_json/{year}/{month}`
  - `month` is zero-based (`0` = January, `11` = December).
  - It checks the current UTC month and the previous two months, newest first.
  - The first nine positions in `averages.total` map to overlapping three-month
    seasons centered on the issue month and the following eight months.
  - Invalid values are skipped without shifting later values to different
    seasons; the fetcher does not fall back to individual models or HTML pages.
- JAMSTEC fetcher parses release split from `SINTEX_DMI.csv` and emits DMI forecast batch.

## Tests

```bash
uv run pytest
cd frontend && npm test -- --run
```

## Acknowledgments

Data providers:
- NOAA PSL: https://psl.noaa.gov
- IRI ENSO forecast plume JSON: https://ensoforecast.iri.columbia.edu/plumes_json/
- JAMSTEC SINTEX-F DMI: https://www.jamstec.go.jp/virtualearth/data/SINTEX/SINTEX_DMI.csv
