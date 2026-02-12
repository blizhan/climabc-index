import { describe, expect, it } from "vitest";
import type { ENSODataPoint, ForecastBatch } from "../types/enso";
import {
  buildTimelineDates,
  buildForecastSeriesData,
  buildTimelineZoomRange,
} from "./timelineData";

describe("timeline forecast projection", () => {
  it("includes future forecast target months in timeline dates", () => {
    const observations: ENSODataPoint[] = [
      {
        date: "2025-09",
        nino34: -0.2,
        nino12: -0.1,
        nino3: -0.2,
        nino4: -0.1,
        soi: 0.3,
        oni: -0.2,
      },
      {
        date: "2025-10",
        nino34: -0.1,
        nino12: 0.0,
        nino3: -0.1,
        nino4: 0.0,
        soi: 0.4,
        oni: -0.1,
      },
    ];
    const forecasts: ForecastBatch[] = [
      {
        id: "forecast-iri-2025-10",
        issuedDate: "2025-10",
        targetDates: ["2025-11", "2025-12"],
        data: [{ nino34: 0.2 }, { nino34: 0.3 }],
        isHistorical: false,
      },
    ];

    const dates = buildTimelineDates(observations, forecasts);

    expect(dates).toEqual(["2025-09", "2025-10", "2025-11", "2025-12"]);
  });

  it("maps jamstec dmi values onto timeline", () => {
    const dates = ["2025-09", "2025-10", "2025-11", "2025-12"];
    const forecast: ForecastBatch = {
      id: "forecast-jamstec-2025-10",
      issuedDate: "2025-10",
      targetDates: ["2025-11", "2025-12"],
      data: [{ dmi: 0.4 }, { dmi: 0.6 }],
      isHistorical: false,
    };

    const values = buildForecastSeriesData(dates, forecast, "dmi");

    expect(values).toEqual([null, null, 0.4, 0.6]);
  });

  it("moves zoom window near selected historical forecast batch", () => {
    const dates = Array.from({ length: 48 }, (_, idx) => {
      const year = 2023 + Math.floor(idx / 12);
      const month = (idx % 12) + 1;
      return `${year}-${String(month).padStart(2, "0")}`;
    });
    const selectedForecast: ForecastBatch = {
      id: "forecast-iri-2024-06",
      issuedDate: "2024-06",
      targetDates: ["2024-07", "2024-08"],
      data: [{ nino34: 0.5 }, { nino34: 0.6 }],
      isHistorical: true,
    };

    const range = buildTimelineZoomRange(dates, selectedForecast, "2026-12");

    expect(range.end).toBeLessThan(100);
    expect(range.start).toBeLessThan(range.end);
    expect(range.start).toBeLessThan(20);
  });

  it("keeps default zoom near current month without historical selection", () => {
    const dates = Array.from({ length: 48 }, (_, idx) => {
      const year = 2023 + Math.floor(idx / 12);
      const month = (idx % 12) + 1;
      return `${year}-${String(month).padStart(2, "0")}`;
    });

    const range = buildTimelineZoomRange(dates, null, "2026-06");

    expect(range.end).toBe(100);
    expect(range.start).toBeGreaterThan(0);
  });
});
