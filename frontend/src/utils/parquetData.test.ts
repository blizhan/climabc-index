import { describe, expect, it } from 'vitest';
import {
  resolveRepoDataBaseUrl,
  groupForecastRows,
  buildForecastFilePaths,
  type ForecastParquetRow,
} from './parquetData';

describe('parquet runtime data helpers', () => {
  it('builds raw GitHub data base url from github pages location', () => {
    const base = resolveRepoDataBaseUrl({
      hostname: 'blizhan.github.io',
      pathname: '/climabc-index/',
      explicitBaseUrl: '',
    });

    expect(base).toBe('https://raw.githubusercontent.com/blizhan/climabc-index/main/data');
  });

  it('builds unique forecast parquet file paths from index rows', () => {
    const paths = buildForecastFilePaths(
      [
        { metric: 'nino34', issued_date: '2026-01' },
        { metric: 'nino34', issued_date: '2026-01' },
        { metric: 'dmi', issued_date: '2026-01' },
      ],
      'https://raw.githubusercontent.com/blizhan/climabc-index/main/data',
    );

    expect(paths).toEqual([
      {
        metric: 'dmi',
        issuedDate: '2026-01',
        url: 'https://raw.githubusercontent.com/blizhan/climabc-index/main/data/forecasts/dmi/2026-01.parquet',
      },
      {
        metric: 'nino34',
        issuedDate: '2026-01',
        url: 'https://raw.githubusercontent.com/blizhan/climabc-index/main/data/forecasts/nino34/2026-01.parquet',
      },
    ]);
  });

  it('groups forecast parquet rows into batches sorted by issued date', () => {
    const rows: ForecastParquetRow[] = [
      {
        forecast_id: 'forecast-iri-2026-01',
        source: 'iri',
        issued_date: '2026-01',
        target_date: '2026-02',
        metric: 'nino34',
        value: 0.5,
        is_historical: false,
      },
      {
        forecast_id: 'forecast-jamstec-2026-01',
        source: 'jamstec',
        issued_date: '2026-01',
        target_date: '2026-02',
        metric: 'dmi',
        value: 0.2,
        is_historical: false,
      },
      {
        forecast_id: 'forecast-iri-2025-12',
        source: 'iri',
        issued_date: '2025-12',
        target_date: '2026-01',
        metric: 'nino34',
        value: 0.4,
        is_historical: true,
      },
    ];

    const batches = groupForecastRows(rows);

    expect(batches.map((item) => item.issuedDate)).toEqual(['2026-01', '2025-12']);
    expect(batches[0].targetDates).toEqual(['2026-02']);
    expect(batches[0].data[0]).toEqual({ dmi: 0.2, nino34: 0.5 });
    expect(batches[0].id).toBe('batch-2026-01');
    expect(batches[0].source).toBe('mixed');
  });
});
