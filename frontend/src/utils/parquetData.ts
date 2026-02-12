import type { DataSet, ENSODataPoint, ENSOValues, ForecastBatch, MetricKey } from '../types/enso';

export interface ForecastParquetRow {
  forecast_id: string;
  source: string;
  issued_date: string;
  target_date: string;
  metric: string;
  value: number;
  is_historical: boolean;
}

export interface ForecastIndexRow {
  metric: string;
  issued_date: string;
}

interface ResolveBaseUrlInput {
  hostname: string;
  pathname: string;
  explicitBaseUrl?: string;
}

interface ForecastFilePath {
  metric: string;
  issuedDate: string;
  url: string;
}

interface HyparquetModule {
  asyncBufferFromUrl: (input: { url: string }) => Promise<unknown>;
  parquetReadObjects: (input: {
    file: unknown;
    columns?: string[];
  }) => Promise<Array<Record<string, unknown>>>;
}

const OBSERVATION_METRICS: MetricKey[] = [
  'nino34',
  'nino12',
  'nino3',
  'nino4',
  'soi',
  'oni',
  'dmi',
  'tni',
  'censo',
  'ao',
  'pdo',
  'wp',
  'amo_us',
  'amo_sm',
  'dmiwest',
  'dmieast',
  'nao',
  'np',
  'tpi',
  'glbts',
  'glbtssst',
];

function _stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

function _isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function _toNumber(value: unknown): number | null {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

async function _loadHyparquet(): Promise<HyparquetModule> {
  const moduleUrl = 'https://cdn.jsdelivr.net/npm/hyparquet@1.8.4/+esm';
  return import(
    /* @vite-ignore */ moduleUrl
  ) as Promise<HyparquetModule>;
}

async function _readParquetObjects(
  url: string,
  columns?: string[],
): Promise<Array<Record<string, unknown>>> {
  const { asyncBufferFromUrl, parquetReadObjects } = await _loadHyparquet();
  const file = await asyncBufferFromUrl({ url });
  return parquetReadObjects({ file, columns });
}

async function _readParquetOrEmpty(
  url: string,
  columns?: string[],
): Promise<Array<Record<string, unknown>>> {
  try {
    return await _readParquetObjects(url, columns);
  } catch {
    return [];
  }
}

export function resolveRepoDataBaseUrl({
  hostname,
  pathname,
  explicitBaseUrl,
}: ResolveBaseUrlInput): string {
  const manualBase = (explicitBaseUrl || '').trim();
  if (manualBase.length > 0) {
    return _stripTrailingSlash(manualBase);
  }

  if (hostname.endsWith('.github.io')) {
    const owner = hostname.split('.')[0];
    const repo = pathname.split('/').filter(Boolean)[0];
    if (owner && repo) {
      return `https://raw.githubusercontent.com/${owner}/${repo}/main/data`;
    }
  }

  return '/data';
}

export function buildForecastFilePaths(
  indexRows: ForecastIndexRow[],
  baseUrl: string,
): ForecastFilePath[] {
  const normalizedBase = _stripTrailingSlash(baseUrl);
  const pairSet = new Set<string>();
  const items: ForecastFilePath[] = [];

  for (const row of indexRows) {
    const metric = String(row.metric || '').trim();
    const issuedDate = String(row.issued_date || '').trim();
    if (!metric || !issuedDate) {
      continue;
    }

    const pairKey = `${metric}@@${issuedDate}`;
    if (pairSet.has(pairKey)) {
      continue;
    }
    pairSet.add(pairKey);

    items.push({
      metric,
      issuedDate,
      url: `${normalizedBase}/forecasts/${metric}/${issuedDate}.parquet`,
    });
  }

  items.sort((left, right) => {
    const metricOrder = left.metric.localeCompare(right.metric);
    if (metricOrder !== 0) {
      return metricOrder;
    }
    return right.issuedDate.localeCompare(left.issuedDate);
  });

  return items;
}

export function groupForecastRows(rows: ForecastParquetRow[]): ForecastBatch[] {
  const byIssue = new Map<
    string,
    {
      byTarget: Map<string, ENSOValues>;
      allHistorical: boolean;
    }
  >();

  for (const row of rows) {
    const issued = String(row.issued_date || '').trim();
    const target = String(row.target_date || '').trim();
    const metric = String(row.metric || '').trim();
    const value = _toNumber(row.value);
    if (!issued || !target || !metric || value === null) {
      continue;
    }

    const issueState = byIssue.get(issued) || {
      byTarget: new Map<string, ENSOValues>(),
      allHistorical: true,
    };

    const point = issueState.byTarget.get(target) || {};
    (point as Record<string, number>)[metric] = value;
    issueState.byTarget.set(target, point);
    issueState.allHistorical = issueState.allHistorical && Boolean(row.is_historical);

    byIssue.set(issued, issueState);
  }

  const batches: ForecastBatch[] = Array.from(byIssue.entries())
    .sort((left, right) => right[0].localeCompare(left[0]))
    .map(([issuedDate, state]) => {
      const targetDates = Array.from(state.byTarget.keys()).sort((left, right) =>
        left.localeCompare(right),
      );
      const data = targetDates.map((targetDate) => state.byTarget.get(targetDate) || {});

      return {
        id: `batch-${issuedDate}`,
        source: 'mixed',
        issuedDate,
        targetDates,
        data,
        isHistorical: state.allHistorical,
      };
    });

  return batches;
}

function _mergeObservationRows(
  observationRowsByMetric: Record<string, Array<Record<string, unknown>>>,
): ENSODataPoint[] {
  const byDate = new Map<string, ENSOValues>();

  for (const [metric, rows] of Object.entries(observationRowsByMetric)) {
    for (const row of rows) {
      const date = String(row.date || '').slice(0, 7);
      const value = _toNumber(row.value);
      if (!date || value === null) {
        continue;
      }

      const point = byDate.get(date) || {};
      (point as Record<string, unknown>)[metric] = value;
      byDate.set(date, point);
    }
  }

  return Array.from(byDate.entries())
    .sort((left, right) => left[0].localeCompare(right[0]))
    .map(([date, values]) => ({
      date,
      ...values,
    }));
}

function _normalizeMetric(metric: string): MetricKey | null {
  const key = metric as MetricKey;
  if (OBSERVATION_METRICS.includes(key)) {
    return key;
  }
  return null;
}

function _toForecastRows(rows: Array<Record<string, unknown>>): ForecastParquetRow[] {
  const parsed: ForecastParquetRow[] = [];
  for (const row of rows) {
    const value = _toNumber(row.value);
    const metric = _normalizeMetric(String(row.metric || ''));
    if (value === null || !metric) {
      continue;
    }

    parsed.push({
      forecast_id: String(row.forecast_id || ''),
      source: String(row.source || 'unknown'),
      issued_date: String(row.issued_date || ''),
      target_date: String(row.target_date || ''),
      metric,
      value,
      is_historical:
        row.is_historical === true ||
        row.is_historical === 'true' ||
        (_isFiniteNumber(row.is_historical) && row.is_historical !== 0),
    });
  }
  return parsed;
}

export async function loadDatasetFromParquet(options?: {
  explicitBaseUrl?: string;
}): Promise<DataSet> {
  const baseUrl = resolveRepoDataBaseUrl({
    hostname: window.location.hostname,
    pathname: window.location.pathname,
    explicitBaseUrl: options?.explicitBaseUrl,
  });

  const observationRowsByMetric: Record<string, Array<Record<string, unknown>>> = {};
  await Promise.all(
    OBSERVATION_METRICS.map(async (metric) => {
      const url = `${baseUrl}/observations/${metric}.parquet`;
      observationRowsByMetric[metric] = await _readParquetOrEmpty(url, ['date', 'value']);
    }),
  );

  const observations = _mergeObservationRows(observationRowsByMetric);

  const indexRowsRaw = await _readParquetOrEmpty(`${baseUrl}/forecasts/_index.parquet`, [
    'metric',
    'issued_date',
  ]);

  const filePaths = buildForecastFilePaths(
    indexRowsRaw.map((row) => ({
      metric: String(row.metric || ''),
      issued_date: String(row.issued_date || ''),
    })),
    baseUrl,
  );

  const forecastRowsNested = await Promise.all(
    filePaths.map((entry) => _readParquetOrEmpty(entry.url)),
  );
  const forecastRows = _toForecastRows(forecastRowsNested.flat());
  const forecasts = groupForecastRows(forecastRows);

  return {
    observations,
    forecasts,
    latestForecast: forecasts[0] || null,
    selectedForecast: null,
  };
}
