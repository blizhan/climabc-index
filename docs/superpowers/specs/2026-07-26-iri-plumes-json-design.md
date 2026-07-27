# IRI ENSO `plumes_json` Fetcher Design

## Goal

Replace the IRI ENSO HTML scraping path with direct requests to the JSON endpoint used by the site's Interactive Chart.

## Scope

- Request only `https://ensoforecast.iri.columbia.edu/plumes_json/{year}/{month}`.
- Treat `month` as a zero-based month number (`0` for January through `11` for December).
- Starting with the current UTC month, consider exactly three months in descending order: current month, previous month, and two months ago.
- Use `averages.total` as the Niño 3.4 forecast values.
- Do not request or parse the IRI `current` or monthly quick-look HTML pages.
- Change the configured IRI recent batch count from six to three.

The IRI configuration becomes JSON-specific:

```yaml
iri:
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
      unit: "°C"
```

The obsolete `url_template`, `current_url`, and `params` HTML settings are removed. The category remains `enso`; the name, description, and unit are corrected to describe Niño 3.4 anomaly values rather than probabilities.

## Data Mapping

Each successful JSON response represents one issue month and contains up to nine forecast values in `averages.total`. The first nine array positions map, without compaction, to nine overlapping three-month seasons centered on the issue month and the following eight months:

| Issue month | First season | Example sequence |
| --- | --- | --- |
| January | DJF | DJF, JFM, FMA, MAM, AMJ, MJJ, JJA, JAS, ASO |
| July | JJA | JJA, JAS, ASO, SON, OND, NDJ, DJF, JFM, FMA |
| December | NDJ | NDJ, DJF, JFM, FMA, MAM, AMJ, MJJ, JJA, JAS |

The existing forecast batch conversion remains responsible for assigning timestamps and producing the frontend batch schema.

Arrays shorter than nine positions produce only the corresponding early seasons. Entries after position nine are ignored. An invalid value leaves its season absent; later values retain their original season positions and never shift forward.

## Error Handling

Each month is independent. A warning is logged with the source month and reason, then the next older month is attempted when:

- the request raises an exception;
- the response status is 400 or greater;
- the response body is not valid JSON;
- `averages.total` is missing or is not a list;
- no usable values remain.

Within `averages.total`, `null`, booleans, numeric strings, other non-numeric values, non-finite values, and the IRI missing marker `-999` or `-999.0` are ignored. A partially populated month remains usable.

The fetcher never substitutes HTML data and never derives an average from individual models.

## Compatibility

- Preserve the public `fetch_batch()` and `fetch_batches()` methods.
- Preserve descending issue-date ordering.
- Preserve `start_issue_date` as the starting month when explicitly supplied; timezone-aware and day-level inputs are normalized to a timezone-naive month start. Otherwise use the current UTC month.
- Retain existing HTML parsing helpers for compatibility with current imports and tests, but remove them from the production fetch path.
- Limit the search to exactly three candidate months. Requests proceed from newest to oldest and stop early once `max_batches` usable batches have been collected. `max_batches` cannot expand the three-month search window.
- Positive integer `max_batches` values are accepted. Zero and negative integers are normalized to one, preserving the existing behavior. Non-integer values raise `ValueError`.

## Tests

Tests will use mocked HTTP responses and cover:

1. zero-based endpoint URL construction;
2. mapping `averages.total` into the correct nine seasons;
3. current-month-to-two-months-ago request order, including year rollover;
4. skipping failed, malformed, or empty monthly responses;
5. preserving positional season alignment for short, long, and partially invalid arrays;
6. stopping after the requested batch count;
7. descending result ordering;
8. configuration default of three recent IRI batches.
9. making no `current` or quick-look HTML request;
10. refusing to fall back to individual `models` when `averages.total` is absent or invalid;
11. logging skipped monthly responses.

No test will access the live IRI service.
