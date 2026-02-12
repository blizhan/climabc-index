import type { ENSODataPoint, ForecastBatch } from "../types/enso";
import { METRICS } from "../types/enso";
import type { Language } from "../i18n";

const METRIC_ORDER = METRICS.map((metric) => metric.key);
const METRIC_LABELS = new Map(METRICS.map((metric) => [metric.key, metric.label]));

function inferSourceFromId(forecastId: string): string {
  const id = forecastId.toLowerCase();
  if (id.includes("jamstec")) {
    return "JAMSTEC";
  }
  if (id.includes("iri")) {
    return "IRI";
  }
  return "UNKNOWN";
}

export function getForecastSourceLabel(forecast: ForecastBatch): string {
  if (forecast.source && forecast.source.trim().length > 0) {
    return forecast.source.toUpperCase();
  }
  return inferSourceFromId(forecast.id);
}

export function extractForecastMetrics(forecast: ForecastBatch): Array<keyof ENSODataPoint> {
  const metricSet = new Set<keyof ENSODataPoint>();
  for (const point of forecast.data) {
    for (const key of Object.keys(point) as Array<keyof ENSODataPoint>) {
      if (typeof point[key] === "number") {
        metricSet.add(key);
      }
    }
  }

  const metrics = Array.from(metricSet);
  metrics.sort((left, right) => {
    const leftOrder = METRIC_ORDER.indexOf(left);
    const rightOrder = METRIC_ORDER.indexOf(right);
    if (leftOrder === -1 && rightOrder === -1) {
      return String(left).localeCompare(String(right));
    }
    if (leftOrder === -1) {
      return 1;
    }
    if (rightOrder === -1) {
      return -1;
    }
    return leftOrder - rightOrder;
  });
  return metrics;
}

export function formatForecastBatchTitle(
  forecast: ForecastBatch,
  language: Language = "zh",
): string {
  const metricLabels = extractForecastMetrics(forecast).map(
    (metric) => METRIC_LABELS.get(metric) ?? String(metric).toUpperCase(),
  );
  const metricPart =
    metricLabels.length > 0
      ? metricLabels.join(" / ")
      : language === "en"
        ? "Unknown Metric"
        : "未知指数";
  if (language === "en") {
    return `${metricPart} · ${forecast.issuedDate} release`;
  }
  return `${metricPart} ${forecast.issuedDate}发布`;
}

export function formatForecastBatchLabel(
  forecast: ForecastBatch,
  language: Language = "zh",
): string {
  return language === "en" ? `${forecast.issuedDate} batch` : `${forecast.issuedDate}批次`;
}

export function getForecastIssueMonths(forecasts: ForecastBatch[]): string[] {
  const months = new Set<string>();
  for (const forecast of forecasts) {
    if (forecast.issuedDate) {
      months.add(forecast.issuedDate);
    }
  }
  return Array.from(months).sort((left, right) => right.localeCompare(left));
}

export function buildMonthlyForecastBatch(
  forecasts: ForecastBatch[],
  issueMonth: string,
): ForecastBatch | null {
  const monthBatches = forecasts.filter((forecast) => forecast.issuedDate === issueMonth);
  if (monthBatches.length === 0) {
    return null;
  }

  const mergedByTarget = new Map<string, Partial<ENSODataPoint>>();
  for (const batch of monthBatches) {
    batch.targetDates.forEach((targetDate, index) => {
      const point = batch.data[index];
      if (!point || typeof point !== "object") {
        return;
      }

      const mergedPoint = mergedByTarget.get(targetDate) ?? {};
      for (const [rawKey, rawValue] of Object.entries(point)) {
        if (typeof rawValue !== "number" || !Number.isFinite(rawValue)) {
          continue;
        }
        const key = rawKey as keyof ENSODataPoint;
        if (key === "date") {
          continue;
        }
        (mergedPoint as Record<string, number>)[key] = rawValue;
      }
      mergedByTarget.set(targetDate, mergedPoint);
    });
  }

  const targetDates = Array.from(mergedByTarget.keys()).sort((left, right) => left.localeCompare(right));
  const data = targetDates.map((targetDate) => mergedByTarget.get(targetDate) ?? {});

  return {
    id: `batch-${issueMonth}`,
    source: "mixed",
    issuedDate: issueMonth,
    targetDates,
    data,
    isHistorical: monthBatches.every((batch) => batch.isHistorical),
  };
}

export function findLatestForecastForMetric(
  forecasts: ForecastBatch[],
  metric: keyof ENSODataPoint,
): ForecastBatch | null {
  return (
    forecasts
      .filter((forecast) => extractForecastMetrics(forecast).includes(metric))
      .sort((left, right) => right.issuedDate.localeCompare(left.issuedDate))[0] ?? null
  );
}
