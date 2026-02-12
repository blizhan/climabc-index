import type { ENSODataPoint, ForecastBatch, MetricKey } from "../types/enso";
import { findLatestForecastForMetric } from "./forecastMetadata";

export interface DataSnapshotRow {
  date: string;
  rowType: "observation" | "forecast";
  issuedDate: string | null;
  values: Partial<Record<MetricKey, number>>;
}

function toComparableMonth(monthToken: string): number {
  const [yearStr, monthStr] = monthToken.split("-");
  const year = Number.parseInt(yearStr ?? "", 10);
  const month = Number.parseInt(monthStr ?? "", 10);
  if (!Number.isFinite(year) || !Number.isFinite(month)) {
    return Number.NEGATIVE_INFINITY;
  }
  return year * 100 + month;
}

function pickMetricValues(
  source: Partial<Record<MetricKey, unknown>>,
  metrics: Array<MetricKey>,
): Partial<Record<MetricKey, number>> {
  const values: Partial<Record<MetricKey, number>> = {};
  for (const metric of metrics) {
    const metricValue = source[metric];
    if (typeof metricValue === "number") {
      values[metric] = metricValue;
    }
  }
  return values;
}

export function buildDataSnapshotRows(
  observations: ENSODataPoint[],
  forecasts: ForecastBatch[],
  forecastBatch: ForecastBatch | null,
  metrics: Array<MetricKey>,
  observationLimit = 18,
  forecastLimit = 12,
): DataSnapshotRow[] {
  const observationRows = observations
    .slice()
    .sort((a, b) => toComparableMonth(b.date) - toComparableMonth(a.date))
    .slice(0, Math.max(0, observationLimit))
    .map<DataSnapshotRow>((point) => ({
      date: point.date,
      rowType: "observation",
      issuedDate: null,
      values: pickMetricValues(point, metrics),
    }));

  const forecastRowsByDate = new Map<string, DataSnapshotRow>();
  const selectedBatchByMetric = new Map<MetricKey, ForecastBatch>();
  for (const metric of metrics) {
    const resolvedBatch = forecastBatch ?? findLatestForecastForMetric(forecasts, metric);
    if (resolvedBatch) {
      selectedBatchByMetric.set(metric, resolvedBatch);
    }
  }

  for (const metric of metrics) {
    const resolvedBatch = selectedBatchByMetric.get(metric);
    if (!resolvedBatch) {
      continue;
    }

    const pairCount = Math.min(
      resolvedBatch.targetDates.length,
      resolvedBatch.data.length,
      Math.max(0, forecastLimit),
    );
    for (let i = 0; i < pairCount; i += 1) {
      const date = resolvedBatch.targetDates[i];
      const metricValue = resolvedBatch.data[i]?.[metric];
      if (typeof metricValue !== "number") {
        continue;
      }

      const existing = forecastRowsByDate.get(date);
      if (existing) {
        existing.values[metric] = metricValue;
        continue;
      }

      forecastRowsByDate.set(date, {
        date,
        rowType: "forecast",
        issuedDate: forecastBatch ? resolvedBatch.issuedDate : null,
        values: { [metric]: metricValue },
      });
    }
  }

  const forecastRows = Array.from(forecastRowsByDate.values());

  return [...observationRows, ...forecastRows].sort((a, b) => {
    const delta = toComparableMonth(b.date) - toComparableMonth(a.date);
    if (delta !== 0) {
      return delta;
    }
    if (a.rowType === b.rowType) {
      return 0;
    }
    return a.rowType === "observation" ? -1 : 1;
  });
}
