# ClimABC Index - TODO List

## Overview

This document tracks the implementation status of features defined in AGENTS.md.

**Last Updated:** 2026-02-01
**Status Key:** ✅ Completed | ⏳ In Progress | 🔴 High Priority | 🟡 Medium Priority | 🟢 Low Priority

---

## ✅ Completed

### Core Architecture
- [x] Fetcher template method pattern (async httpx + tenacity)
- [x] PSL Fetcher with 21 indicators (tested)
- [x] YAML configuration system (per-source + per-indicator overrides)
- [x] Base utility methods (_is_valid_year, _replace_missing_with_nan, _wide_to_long_transform)

### Testing
- [x] pytest setup with fixtures
- [x] BaseFetcher utility tests
- [x] PSL fetcher integration tests
- [x] Test factory functions (create_fetcher_tests, create_parsing_tests)
- [x] Makefile with test/lint/fmt commands

### Documentation
- [x] README.md with basic usage
- [x] AGENTS.md with design decisions
- [x] architecture.md with system overview
- [x] docs/ directory structure for GitHub Pages

---

## 🔴 High Priority (Next Up)

### 1. CLI Implementation
**Status:** Pending  
**Description:** Command-line interface using `click`

Tasks:
- [ ] Create `src/climabc/cli/__init__.py` with main entry point
- [ ] Implement `climabc index list` - List all indicators
- [ ] Implement `climabc index fetch <indicator>` - Fetch specific indicator
- [ ] Implement `climabc index fetch-all` - Fetch all indicators
- [ ] Implement `climabc index status` - Check data source status
- [ ] Add entry point to pyproject.toml: `climabc = "climabc.cli:cli"`

**Files:**
- `src/climabc/cli/__init__.py`
- `src/climabc/cli/commands/index.py`

---

### 2. NCEI Fetcher
**Status:** Pending  
**Description:** NOAA NCEI data source implementation

Tasks:
- [ ] Create `src/climabc/fetchers/ncei.py`
- [ ] Implement `_parse_data()` for NCEI format (year-month-value)
- [ ] Handle skiprows for headers
- [ ] Test with sample data
- [ ] Add to `src/climabc/fetchers/__init__.py`

**Configuration:** Already in `indicators.yaml` (nina_all, pdo, amo, iod)

**Files:**
- `src/climabc/fetchers/ncei.py`
- `tests/unit/test_ncei_fetcher.py`

---

### 3. GitHub Actions CI/CD
**Status:** Pending  
**Description:** Automated data update workflow

Tasks:
- [ ] Create `.github/workflows/update-data.yml`
- [ ] Configure scheduled trigger (every 3 days)
- [ ] Setup matrix strategy for parallel fetching (psl, ncei, iri, jamstec)
- [ ] Configure artifact upload/download
- [ ] Setup auto-commit to `data-update` branch
- [ ] Add error handling and notifications

**Files:**
- `.github/workflows/update-data.yml`

---

### 4. Data Storage Module
**Status:** Pending  
**Description:** Local and Git storage for fetched data

Tasks:
- [ ] Create `src/climabc/storage/__init__.py`
- [ ] Implement `storage/local.py` - Save to Parquet files
  - Path: `~/.climabc/data/{source}/{indicator}/{date}.parquet`
  - Create `latest.parquet` symlink
- [ ] Implement `storage/git.py` - Commit to data-update branch
  - Handle branch checkout
  - Git add/commit/push
- [ ] Implement retention policy (90 days full, 365 days monthly)

**Files:**
- `src/climabc/storage/local.py`
- `src/climabc/storage/git.py`

---

## 🟡 Medium Priority

### 5. IRI Fetcher
**Status:** Pending  
**Description:** IRI/CPC forecast data (HTML table parsing)

Tasks:
- [ ] Create `src/climabc/fetchers/iri.py`
- [ ] Add `beautifulsoup4` dependency
- [ ] Implement HTML table parsing
- [ ] Handle dynamic URL construction (year/month placeholders)
- [ ] Test with mocked HTML responses

**Configuration:** `iri.enso_prob` in `indicators.yaml`

---

### 6. JAMSTEC Fetcher
**Status:** Pending  
**Description:** JAMSTEC CSV data

Tasks:
- [ ] Create `src/climabc/fetchers/jamstec.py`
- [ ] Implement CSV parsing with pandas
- [ ] Handle potential header rows
- [ ] Test with sample CSV data

**Configuration:** `jamstec.dmi` in `indicators.yaml`

---

### 7. RSS Generation
**Status:** Pending  
**Description:** RSS feeds for data updates and alerts

Tasks:
- [ ] Create `src/climabc/rss/__init__.py`
- [ ] Add `feedgen` dependency
- [ ] Implement `generate_full_feed()` - All updates
- [ ] Implement `generate_alert_feed()` - Significant changes only
- [ ] Define alert conditions:
  - Niño 3.4 crosses ±0.5°C
  - SOI exceeds ±7
  - New forecast data available
- [ ] Generate `feed.xml` and `alerts.xml` in docs/

**Files:**
- `src/climabc/rss/generator.py`
- `docs/feed.xml` (template)

---

### 8. Data Validation
**Status:** Pending  
**Description:** Data quality and range validation

Tasks:
- [ ] Create `src/climabc/validator.py`
- [ ] Implement value range checks:
  - SST: -2°C to 35°C
  - Pressure: reasonable ranges
  - Index values: source-specific ranges
- [ ] Implement consistency checks:
  - Timestamp continuity
  - No sudden jumps
- [ ] Implement cross-validation between sources

---

### 9. Frontend Visualization
**Status:** Pending  
**Description:** GitHub Pages dashboard with Plotly.js

Tasks:
- [ ] Create `docs/assets/js/charts/`
- [ ] Implement time series chart component
- [ ] Implement multi-source comparison chart
- [ ] Create indicator detail pages
- [ ] Add data table view
- [ ] Generate static JSON data files for frontend

**Files:**
- `docs/assets/js/charts/timeseries.js`
- `docs/assets/data/` (JSON files)

---

## 🟢 Low Priority (Future)

### 10. Data Export
**Status:** Future  
**Description:** Export to various formats

Tasks:
- [ ] CSV export
- [ ] JSON export
- [ ] NetCDF export (climate data standard)
- [ ] GRIB export (forecast data)

---

### 11. Logging & Monitoring
**Status:** Future  
**Description:** Structured logging and metrics

Tasks:
- [ ] Add structured logging (structlog)
- [ ] Log fetch attempts, successes, failures
- [ ] Track data source health
- [ ] Metrics collection (prometheus/grafana)

---

### 12. API Server
**Status:** Future  
**Description:** REST API for programmatic access

Tasks:
- [ ] FastAPI or Flask setup
- [ ] Endpoints:
  - GET /api/v1/indicators
  - GET /api/v1/indicators/{id}/data
  - GET /api/v1/sources
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Rate limiting

---

## Next Steps Recommendations

### Option A: Quick Usability (Recommended)
Implement CLI + NCEI + CI/CD first:
1. CLI commands
2. NCEI fetcher (quick win using template method)
3. GitHub Actions workflow
4. Basic data storage

**Result:** Working CLI tool that can fetch and save data.

### Option B: Complete Data Sources
Implement all fetchers first:
1. NCEI, IRI, JAMSTEC fetchers
2. Then storage + validation
3. Then CLI

**Result:** All 4 data sources working before user interface.

### Option C: Visualization First
Focus on frontend:
1. Complete docs/ structure
2. Plotly.js charts
3. Data export for frontend
4. RSS feeds

**Result:** Nice dashboard even with manual data updates.

---

## Contributing

When completing a task:
1. Update this TODO.md (mark as completed)
2. Update AGENTS.md if design changes
3. Add tests for new features
4. Run `make check` before committing

---

## Notes

- **Architecture:** Template method pattern makes adding new fetchers ~20 lines of code
- **Testing:** Use factory functions for quick test coverage
- **CI/CD:** Matrix strategy allows parallel fetching from all sources
- **Storage:** Parquet format for efficiency, Git for versioning
