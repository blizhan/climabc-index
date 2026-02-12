import type { ENSODataPoint, ForecastBatch } from "../types/enso";

function isMonthToken(value: string): boolean {
  return /^\d{4}-\d{2}$/.test(value);
}

export function buildTimelineDates(
  observations: ENSODataPoint[],
  forecasts: ForecastBatch[],
): string[] {
  const monthSet = new Set<string>();

  for (const point of observations) {
    if (isMonthToken(point.date)) {
      monthSet.add(point.date);
    }
  }
  for (const batch of forecasts) {
    for (const targetDate of batch.targetDates) {
      if (isMonthToken(targetDate)) {
        monthSet.add(targetDate);
      }
    }
  }

  return Array.from(monthSet).sort((a, b) => a.localeCompare(b));
}

export function buildObservationSeriesData(
  dates: string[],
  observations: ENSODataPoint[],
  metric: keyof ENSODataPoint,
): Array<number | null> {
  const byDate = new Map<string, ENSODataPoint>();
  for (const point of observations) {
    byDate.set(point.date, point);
  }

  return dates.map((date) => {
    const value = byDate.get(date)?.[metric];
    return typeof value === "number" ? value : null;
  });
}

export function buildForecastSeriesData(
  dates: string[],
  forecast: ForecastBatch,
  metric: keyof ENSODataPoint,
  observationsByDate?: Map<string, ENSODataPoint>,
): Array<number | null> {
  const seriesData: Array<number | null> = new Array(dates.length).fill(null);

  forecast.targetDates.forEach((targetDate, idx) => {
    const targetIdx = dates.indexOf(targetDate);
    if (targetIdx < 0 || !forecast.data[idx]) {
      return;
    }
    const value = forecast.data[idx][metric];
    if (typeof value === "number") {
      seriesData[targetIdx] = value;
    }
  });

  if (observationsByDate) {
    const firstForecastIndex = seriesData.findIndex((value) => value !== null);
    if (firstForecastIndex > 0) {
      const previousDate = dates[firstForecastIndex - 1];
      const previousValue = observationsByDate.get(previousDate)?.[metric];
      if (typeof previousValue === "number") {
        seriesData[firstForecastIndex - 1] = previousValue;
      }
    }
  }

  return seriesData;
}

interface ZoomRange {
  start: number;
  end: number;
}

function _indexToPercent(index: number, total: number): number {
  if (total <= 1) {
    return 100;
  }
  return (index / (total - 1)) * 100;
}

export function buildTimelineZoomRange(
  dates: string[],
  selectedForecast: ForecastBatch | null,
  nowMonth: string = new Date().toISOString().slice(0, 7),
): ZoomRange {
  if (dates.length <= 1) {
    return { start: 0, end: 100 };
  }

  if (selectedForecast?.isHistorical) {
    let anchorIndex = dates.indexOf(selectedForecast.issuedDate);
    if (anchorIndex < 0) {
      const validTargets = selectedForecast.targetDates
        .map((target) => dates.indexOf(target))
        .filter((index) => index >= 0)
        .sort((left, right) => left - right);
      if (validTargets.length > 0) {
        anchorIndex = Math.max(0, validTargets[0] - 1);
      }
    }

    if (anchorIndex >= 0) {
      const historyMonths = 18;
      const futureMonths = 18;
      const startIndex = Math.max(0, anchorIndex - historyMonths);
      const endIndex = Math.min(dates.length - 1, anchorIndex + futureMonths);
      return {
        start: _indexToPercent(startIndex, dates.length),
        end: _indexToPercent(endIndex, dates.length),
      };
    }
  }

  const nowIndex = dates.findIndex((date) => date >= nowMonth);
  const splitIndex = nowIndex >= 0 ? nowIndex : dates.length;
  return {
    start: Math.max(0, ((splitIndex - 24) / dates.length) * 100),
    end: 100,
  };
}
