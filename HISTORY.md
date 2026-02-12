# Project History

This file tracks the *actual delivered state* of the repository.

## Snapshot (as of 2026-02-12)

- Python package with CLI entry: `climabc`
- Observation pipeline focused on PSL indicators required by current frontend contract
- Forecast pipeline split into source modules under `src/climabc/fetchers/forecast/`
  - IRI (`current` + historical quick-look backfill)
  - JAMSTEC (DMI CSV parsing)
- Data output contract moved to split parquet directories:
  - `data/observations/<metric>.parquet`
  - `data/forecasts/<metric>/<issued_month>.parquet`
- Forecast index file added:
  - `data/forecasts/_index.parquet`
- Frontend supports bilingual UI (ZH/EN), metric filter, forecast batch selector, timeline, and snapshot table
- Frontend reads parquet directly in runtime (no production JSON dependency)
- GitHub Actions automation:
  - data refresh every 5 days (commits `data/`)
  - Pages build/deploy on `main` push with `data/**` ignored

---

## Timeline

### 2026-02-01: Project foundation

- Repository scaffolding, Python packaging, uv-based workflow
- Initial architecture and source configuration strategy (`indicators.yaml`)
- Base observation fetcher pattern established

### 2026-02-01 to 2026-02-10: Observation pipeline hardening

- PSL fetcher became the primary observation source for current frontend contract
- Added missing-marker handling and year/data normalization logic
- Added regression tests around parsing and data cleaning behavior

### 2026-02-10 to 2026-02-12: Forecast integration and storage contract change

- Introduced forecast-specific fetchers:
  - `IriForecastFetcher`
  - `JamstecForecastFetcher`
- Updated IRI URL strategy to support:
  - latest page: `/enso/current/?enso_tab=enso-sst_table`
  - historical pages: `/{year}-{month}-quick-look/?enso_tab=enso-sst_table`
- Replaced legacy monolithic output expectation with split parquet as default
- Added anomaly sanitization before parquet write (missing markers + obvious outliers to NaN)

### 2026-02-12: Frontend and deployment alignment

- Frontend data flow aligned with split parquet + adapter script
- Frontend switched to direct parquet runtime loading
- Historical forecast batch interaction and timeline behavior improved
- Added ZH/EN switch and streamlined source references in UI
- Added CI workflows for:
  - scheduled data refresh (every 5 days)
  - GitHub Pages build/deploy (data-only pushes do not rebuild frontend)

---

## Current Contract (Authoritative)

### CLI `generate`

Primary command:

```bash
uv run climabc generate --split-output-dir data
```

Behavior:
- fetches required observation indicators
- fetches forecast batches from configured forecast sources
- sanitizes anomalies before parquet persistence
- writes split parquet datasets

Optional compatibility outputs (`--output`, `--forecast-output`, `--json-output`) are non-default.

### Data layout

```text
data/
  observations/
    <metric>.parquet
  forecasts/
    _index.parquet
    <metric>/
      <issued_month>.parquet
```

### Frontend loading modes

- Dev: read `/data/...` parquet served by Vite middleware
- Prod (Pages): read parquet from raw GitHub URL (`main/data`)

---

## What was intentionally removed from this history

- Long-form generic process narrative not tied to repository behavior
- Planned-but-not-implemented modules as if they were shipped
- Duplicate architecture explanations already covered in `AGENTS.md` and code

This file is now a concise operational changelog, not a methodology essay.
