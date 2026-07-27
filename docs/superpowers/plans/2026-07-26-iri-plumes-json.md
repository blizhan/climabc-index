# IRI `plumes_json` Fetcher Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace IRI ENSO HTML scraping with a three-month JSON fetch that maps `averages.total` to Niño 3.4 forecast batches.

**Architecture:** Keep `IriForecastFetcher.fetch_batch()` and `fetch_batches()`, but isolate endpoint rendering and strict positional payload parsing in small helpers. `fetch_batches()` checks at most three issue months from newest to oldest, logs each skipped response, and uses the existing `_values_to_batch()` schema converter.

**Tech Stack:** Python, pandas, httpx, pytest, pytest-asyncio, respx, PyYAML, Ruff.

---

## Chunk 1: IRI JSON Fetching

### Task 1: Configure and parse `averages.total`

**Files:**
- Modify: `src/climabc/config/indicators.yaml`
- Modify: `src/climabc/fetchers/forecast/iri.py`
- Modify: `tests/unit/test_forecast_sources.py`

- [ ] **Step 1: Write failing configuration and positional parser tests**

Import `_extract_iri_total_values` from `climabc.fetchers.forecast.iri`, then add:

```python
def test_iri_config_uses_plumes_json_with_three_recent_batches(config):
    source = config["sources"]["iri"]
    indicator = source["indicators"]["enso_prob"]

    assert source["base_url"] == "https://ensoforecast.iri.columbia.edu"
    assert source["recent_batches"] == 3
    assert source["default"]["format"] == "json"
    assert indicator["endpoint_template"] == "/plumes_json/{year}/{month}"
    assert indicator["unit"] == "°C"
    assert "url_template" not in indicator
    assert "current_url" not in indicator
    assert "params" not in indicator


def test_extract_iri_total_values_preserves_season_positions():
    payload = {
        "averages": {
            "total": [
                1,
                1.1,
                None,
                1.3,
                -999,
                1.5,
                "1.6",
                True,
                float("inf"),
                99,
            ]
        },
        "models": [{"data": [99] * 9}],
    }

    values = _extract_iri_total_values(payload, pd.Timestamp("2026-07-20"))

    assert values == [
        ("JJA", 1.0),
        ("JAS", 1.1),
        ("SON", 1.3),
        ("NDJ", 1.5),
    ]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"averages": None},
        {"averages": {}},
        {"averages": {"total": "not-a-list"}},
        {"models": [{"data": [1.0] * 9}]},
    ],
)
def test_extract_iri_total_values_requires_total_average(payload):
    assert _extract_iri_total_values(payload, pd.Timestamp("2026-07-01")) == []
```

- [ ] **Step 2: Run Task 1 tests and verify RED**

Run:

```bash
uv run pytest -q \
  tests/unit/test_forecast_sources.py::test_iri_config_uses_plumes_json_with_three_recent_batches \
  tests/unit/test_forecast_sources.py::test_extract_iri_total_values_preserves_season_positions \
  tests/unit/test_forecast_sources.py::test_extract_iri_total_values_requires_total_average
```

Expected: collection fails because `_extract_iri_total_values` does not exist, and the configuration still contains HTML settings.

- [ ] **Step 3: Implement the configuration and parser**

Change the IRI YAML block to:

```yaml
iri:
  name: "IRI/LDEO Climate Data Library"
  base_url: "https://ensoforecast.iri.columbia.edu"
  type: "forecast"
  recent_batches: 3

  default:
    format: "json"
    frequency: "monthly"

  indicators:
    enso_prob:
      name: "ENSO Niño 3.4 Forecast"
      description: "Multi-model mean Niño 3.4 SST anomaly forecast from IRI"
      endpoint_template: "/plumes_json/{year}/{month}"
      category: "enso"
      unit: "°C"
```

In `iri.py`, import `math`, define:

```python
_SEASONS_BY_CENTER_MONTH = (
    "DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ",
    "JJA", "JAS", "ASO", "SON", "OND", "NDJ",
)
_IRI_SEARCH_MONTHS = 3
```

and add:

```python
def _extract_iri_total_values(
    payload: Any,
    issue_date: pd.Timestamp,
) -> list[tuple[str, float]]:
    if not isinstance(payload, dict):
        return []
    averages = payload.get("averages")
    if not isinstance(averages, dict):
        return []
    total = averages.get("total")
    if not isinstance(total, list):
        return []

    seasons = [
        _SEASONS_BY_CENTER_MONTH[(issue_date.month - 1 + offset) % 12]
        for offset in range(9)
    ]
    values = []
    for index, raw_value in enumerate(total[:9]):
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            continue
        value = float(raw_value)
        if not math.isfinite(value) or value == -999.0:
            continue
        values.append((seasons[index], value))
    return values
```

- [ ] **Step 4: Run Task 1 tests and verify GREEN**

Run the command from Step 2. Expected: all selected cases pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/climabc/config/indicators.yaml src/climabc/fetchers/forecast/iri.py tests/unit/test_forecast_sources.py
git commit -m "test: define IRI plumes JSON mapping"
```

### Task 2: Fetch at most three JSON issue months

**Files:**
- Modify: `src/climabc/fetchers/forecast/iri.py`
- Modify: `tests/unit/test_forecast_sources.py`

- [ ] **Step 1: Write a failing happy-path endpoint test**

Replace the two old HTML workflow tests with:

```python
@pytest.mark.asyncio
async def test_iri_fetcher_uses_plumes_json_total_average(config, mock_respx):
    cfg = deepcopy(config)
    jul_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/6"
    jun_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/5"
    mock_respx.get(jul_url).respond(
        json={"averages": {"total": [1.0, 1.1, None, 1.3, -999, 1.5, 1.6, 1.7, 1.8, 99.0]}}
    )
    mock_respx.get(jun_url).respond(
        json={"averages": {"total": [0.5] * 9}}
    )

    async with IriForecastFetcher(cfg) as fetcher:
        batches = await fetcher.fetch_batches(
            max_batches=2,
            start_issue_date=pd.Timestamp("2026-07-20"),
        )

    assert [batch["issuedDate"] for batch in batches] == ["2026-07", "2026-06"]
    assert batches[0]["targetDates"] == [
        "2026-07", "2026-08", "2026-10", "2026-12",
        "2027-01", "2027-02", "2027-03",
    ]
    assert batches[0]["data"] == [
        {"nino34": 1.0}, {"nino34": 1.1}, {"nino34": 1.3},
        {"nino34": 1.5}, {"nino34": 1.6}, {"nino34": 1.7},
        {"nino34": 1.8},
    ]
    assert [str(call.request.url) for call in mock_respx.calls] == [jul_url, jun_url]
```

- [ ] **Step 2: Run the happy-path test and verify RED**

Run:

```bash
uv run pytest -q tests/unit/test_forecast_sources.py::test_iri_fetcher_uses_plumes_json_total_average
```

Expected: fail because the fetcher still requests HTML quick-look pages.

- [ ] **Step 3: Implement endpoint rendering and the minimal JSON loop**

Replace `_build_issue_month_url()` with:

```python
template = indicator_config.get("endpoint_template")
if not template:
    raise ValueError("IRI forecast indicator requires 'endpoint_template'")
path = template.format(year=issue_date.year, month=issue_date.month - 1)
base_url = str(self.source_config.get("base_url", "")).strip()
return f"{base_url.rstrip('/')}/{path.lstrip('/')}"
```

Replace `fetch_batches()` with the minimal path needed for the test:

- normalize `start_issue_date` to a timezone-naive first day at midnight using `tz_localize(None)` so its calendar month does not shift;
- iterate `range(_IRI_SEARCH_MONTHS)`;
- stop when `len(batches) >= limit`;
- request the rendered endpoint;
- parse `response.json()`;
- call `_extract_iri_total_values(payload, candidate_issue_date)`;
- pass values to `_values_to_batch()`;
- sort descending.

Delete `_build_current_url()` and all HTML fetch calls. Retain the standalone HTML helper functions for compatibility.

- [ ] **Step 4: Run the happy-path test and verify GREEN**

Run the command from Step 2. Expected: pass.

- [ ] **Step 5: Write a failing three-month failure/observability test**

Add `import httpx` and:

```python
@pytest.mark.asyncio
async def test_iri_fetcher_checks_three_months_and_logs_failures(
    config, mock_respx, caplog
):
    cfg = deepcopy(config)
    jan_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/0"
    dec_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2025/11"
    nov_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2025/10"
    mock_respx.get(jan_url).mock(
        side_effect=httpx.ConnectError("offline")
    )
    mock_respx.get(dec_url).respond(text="not-json")
    mock_respx.get(nov_url).respond(
        json={"averages": {"total": [0.25, "0.3", True, None, -999.0]}}
    )

    with caplog.at_level("WARNING", logger="climabc.fetchers.forecast.iri"):
        async with IriForecastFetcher(cfg) as fetcher:
            batches = await fetcher.fetch_batches(
                max_batches=3,
                start_issue_date=pd.Timestamp("2026-01-31", tz="Asia/Shanghai"),
            )

    assert [batch["issuedDate"] for batch in batches] == ["2025-11"]
    assert batches[0]["targetDates"] == ["2025-11"]
    assert batches[0]["data"] == [{"nino34": 0.25}]
    assert [str(call.request.url) for call in mock_respx.calls] == [
        jan_url, dec_url, nov_url
    ]
    assert "2026-01" in caplog.text
    assert "request failed" in caplog.text
    assert "2025-12" in caplog.text
    assert "invalid JSON" in caplog.text
```

This case covers request exceptions, invalid JSON, year rollover, timezone normalization, strict value filtering, exact three-month scope, and logging.

Also add explicit HTTP and empty-total logging coverage:

```python
@pytest.mark.asyncio
async def test_iri_fetcher_logs_http_and_empty_total(config, mock_respx, caplog):
    jul_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/6"
    jun_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/5"
    may_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/4"
    mock_respx.get(jul_url).respond(status_code=503)
    mock_respx.get(jun_url).respond(
        json={"averages": {"total": [None, -999, "1.0"]}}
    )
    mock_respx.get(may_url).respond(
        json={"averages": {"total": [0.2]}}
    )

    with caplog.at_level("WARNING", logger="climabc.fetchers.forecast.iri"):
        async with IriForecastFetcher(deepcopy(config)) as fetcher:
            batches = await fetcher.fetch_batches(
                max_batches=3,
                start_issue_date=pd.Timestamp("2026-07-01"),
            )

    assert [batch["issuedDate"] for batch in batches] == ["2026-05"]
    assert "2026-07" in caplog.text and "HTTP 503" in caplog.text
    assert "2026-06" in caplog.text
    assert "missing usable averages.total" in caplog.text
```

Add current-UTC start coverage by patching the shared clock helper:

```python
@pytest.mark.asyncio
async def test_iri_fetcher_defaults_to_current_utc_month(
    config, mock_respx, monkeypatch
):
    monkeypatch.setattr(
        "climabc.fetchers.forecast.iri._current_month_start",
        lambda: pd.Timestamp("2026-07-01"),
    )
    url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/6"
    mock_respx.get(url).respond(json={"averages": {"total": [1.0]}})

    async with IriForecastFetcher(deepcopy(config)) as fetcher:
        batches = await fetcher.fetch_batches(max_batches=1)

    assert [batch["issuedDate"] for batch in batches] == ["2026-07"]
    assert [str(call.request.url) for call in mock_respx.calls] == [url]
```

- [ ] **Step 6: Run the failure/default tests and verify RED**

Run:

```bash
uv run pytest -q \
  tests/unit/test_forecast_sources.py::test_iri_fetcher_checks_three_months_and_logs_failures \
  tests/unit/test_forecast_sources.py::test_iri_fetcher_logs_http_and_empty_total \
  tests/unit/test_forecast_sources.py::test_iri_fetcher_defaults_to_current_utc_month
```

Expected: fail because per-month failures are not logged and/or do not continue.

- [ ] **Step 7: Implement graceful degradation and warning logs**

Import `logging`, define `logger = logging.getLogger(__name__)`, and handle each boundary independently:

```python
try:
    response = await self.client.get(url)
except Exception as exc:  # noqa: BLE001
    logger.warning("Skipping IRI forecast %s: request failed: %s", issue_key, exc)
    continue
if response.status_code >= 400:
    logger.warning("Skipping IRI forecast %s: HTTP %s", issue_key, response.status_code)
    continue
try:
    payload = response.json()
except ValueError:
    logger.warning("Skipping IRI forecast %s: invalid JSON", issue_key)
    continue
values = _extract_iri_total_values(payload, candidate_issue_date)
if not values:
    logger.warning(
        "Skipping IRI forecast %s: missing usable averages.total", issue_key
    )
    continue
```

Import `_current_month_start` from `.base`, then use this complete loop structure:

```python
if start_issue_date is None:
    issue_start = _current_month_start().normalize().replace(day=1)
else:
    issue_start = pd.Timestamp(start_issue_date)
    if issue_start.tz is not None:
        issue_start = issue_start.tz_localize(None)
    issue_start = issue_start.normalize().replace(day=1)

batches = []
for month_offset in range(_IRI_SEARCH_MONTHS):
    if len(batches) >= limit:
        break
    candidate_issue_date = issue_start - pd.DateOffset(months=month_offset)
    issue_key = candidate_issue_date.strftime("%Y-%m")
    url = self._build_issue_month_url(indicator_config, candidate_issue_date)
    try:
        response = await self.client.get(url)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Skipping IRI forecast %s: request failed: %s", issue_key, exc
        )
        continue
    if response.status_code >= 400:
        logger.warning(
            "Skipping IRI forecast %s: HTTP %s",
            issue_key,
            response.status_code,
        )
        continue
    try:
        payload = response.json()
    except ValueError:
        logger.warning("Skipping IRI forecast %s: invalid JSON", issue_key)
        continue
    values = _extract_iri_total_values(payload, candidate_issue_date)
    if not values:
        logger.warning(
            "Skipping IRI forecast %s: missing usable averages.total",
            issue_key,
        )
        continue
    batch = _values_to_batch(
        values,
        issue_date=candidate_issue_date,
        metric_key="nino34",
        source_label=self.source,
    )
    if batch is not None:
        batches.append(batch)
batches.sort(key=lambda item: item.get("issuedDate", ""), reverse=True)
return batches
```

- [ ] **Step 8: Run Task 2 endpoint tests and verify GREEN**

Run:

```bash
uv run pytest -q \
  tests/unit/test_forecast_sources.py::test_iri_fetcher_uses_plumes_json_total_average \
  tests/unit/test_forecast_sources.py::test_iri_fetcher_checks_three_months_and_logs_failures \
  tests/unit/test_forecast_sources.py::test_iri_fetcher_logs_http_and_empty_total \
  tests/unit/test_forecast_sources.py::test_iri_fetcher_defaults_to_current_utc_month
```

Expected: all four pass.

- [ ] **Step 9: Commit Task 2**

```bash
git add src/climabc/fetchers/forecast/iri.py tests/unit/test_forecast_sources.py
git commit -m "fix: fetch IRI forecasts from plumes JSON"
```

### Task 3: Lock down limits and forbid fallback behavior

**Files:**
- Modify: `src/climabc/fetchers/forecast/iri.py`
- Modify: `tests/unit/test_forecast_sources.py`

- [ ] **Step 1: Write exact failing limit and fallback tests**

Add:

```python
@pytest.mark.asyncio
async def test_iri_fetcher_does_not_fallback_to_models_or_html(config, mock_respx):
    cfg = deepcopy(config)
    expected_urls = [
        "https://ensoforecast.iri.columbia.edu/plumes_json/2026/6",
        "https://ensoforecast.iri.columbia.edu/plumes_json/2026/5",
        "https://ensoforecast.iri.columbia.edu/plumes_json/2026/4",
    ]
    for url in expected_urls:
        mock_respx.get(url).respond(
            json={"models": [{"data": [9.9] * 9}]}
        )

    async with IriForecastFetcher(cfg) as fetcher:
        batches = await fetcher.fetch_batches(
            max_batches=99,
            start_issue_date=pd.Timestamp("2026-07-01"),
        )

    assert batches == []
    requested_urls = [str(call.request.url) for call in mock_respx.calls]
    assert requested_urls == expected_urls
    assert all("quick-look" not in url and "/current/" not in url for url in requested_urls)


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_limit", ["3", 1.5, True, None])
async def test_iri_fetcher_rejects_non_integer_max_batches(
    config, bad_limit
):
    async with IriForecastFetcher(deepcopy(config)) as fetcher:
        with pytest.raises(ValueError, match="max_batches"):
            await fetcher.fetch_batches(max_batches=bad_limit)


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, -2])
async def test_iri_fetcher_normalizes_non_positive_limit(
    config, mock_respx, limit
):
    jul_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/6"
    jun_url = "https://ensoforecast.iri.columbia.edu/plumes_json/2026/5"
    mock_respx.get(jul_url).respond(json={"averages": {"total": [1.0]}})
    mock_respx.get(jun_url).respond(json={"averages": {"total": [2.0]}})

    async with IriForecastFetcher(deepcopy(config)) as fetcher:
        batches = await fetcher.fetch_batches(
            max_batches=limit,
            start_issue_date=pd.Timestamp("2026-07-01"),
        )

    assert [batch["issuedDate"] for batch in batches] == ["2026-07"]
    assert [str(call.request.url) for call in mock_respx.calls] == [jul_url]


@pytest.mark.asyncio
async def test_iri_fetch_batch_delegates_to_one_batch(config):
    expected = {"issuedDate": "2026-07"}
    fetcher = IriForecastFetcher(deepcopy(config))
    fetcher.fetch_batches = AsyncMock(return_value=[expected])
    try:
        assert await fetcher.fetch_batch() == expected
        fetcher.fetch_batches.assert_awaited_once_with(max_batches=1)
    finally:
        await fetcher.client.aclose()
```

Import `AsyncMock` from `unittest.mock`.

- [ ] **Step 2: Run Task 3 tests and verify RED**

Run:

```bash
uv run pytest -q \
  tests/unit/test_forecast_sources.py::test_iri_fetcher_does_not_fallback_to_models_or_html \
  tests/unit/test_forecast_sources.py::test_iri_fetcher_rejects_non_integer_max_batches \
  tests/unit/test_forecast_sources.py::test_iri_fetcher_normalizes_non_positive_limit \
  tests/unit/test_forecast_sources.py::test_iri_fetch_batch_delegates_to_one_batch
```

Expected: limit validation cases fail until strict validation is added; other cases document retained behavior and may already pass.

- [ ] **Step 3: Implement strict limit validation**

At the start of `fetch_batches()`:

```python
if isinstance(max_batches, bool) or not isinstance(max_batches, int):
    raise ValueError("max_batches must be an integer")
limit = max(1, max_batches)
```

Do not add a model fallback or any HTML request.

- [ ] **Step 4: Run Task 3 tests and verify GREEN**

Run the command from Step 2. Expected: all selected cases pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/climabc/fetchers/forecast/iri.py tests/unit/test_forecast_sources.py
git commit -m "test: enforce IRI forecast fetch boundaries"
```

### Task 4: Complete verification

**Files:**
- Verify only.

- [ ] **Step 1: Run the focused forecast suite**

```bash
uv run pytest -q tests/unit/test_forecast_sources.py
```

Expected: all forecast source tests pass.

- [ ] **Step 2: Run the complete regression suite**

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 3: Run lint**

```bash
uv run ruff check src tests
```

Expected: zero lint errors.

- [ ] **Step 4: Run a non-gating live smoke check**

Run:

```bash
uv run python - <<'PY'
import asyncio
from pathlib import Path
import yaml
from climabc.fetchers.forecast.iri import IriForecastFetcher

async def main():
    config = yaml.safe_load(
        Path("src/climabc/config/indicators.yaml").read_text()
    )
    async with IriForecastFetcher(config) as fetcher:
        batches = await fetcher.fetch_batches(max_batches=1)
    assert batches
    assert batches[0]["source"] == "iri"
    assert batches[0]["data"]
    print(batches[0]["issuedDate"], len(batches[0]["data"]))

asyncio.run(main())
PY
```

If the network and IRI endpoint are available, expect an issue month and positive forecast count. Otherwise report the external failure separately without weakening the mocked-test gate.

- [ ] **Step 5: Inspect final diff**

```bash
git status --short
git diff --check HEAD~3..HEAD
git diff --stat HEAD~3..HEAD
```

Expected: only the planned IRI configuration, fetcher, tests, and planning documents changed; no whitespace errors.
