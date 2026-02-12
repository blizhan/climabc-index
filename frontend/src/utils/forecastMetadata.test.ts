import { describe, expect, it } from "vitest";
import type { ForecastBatch } from "../types/enso";
import {
  buildMonthlyForecastBatch,
  extractForecastMetrics,
  findLatestForecastForMetric,
  getForecastIssueMonths,
  formatForecastBatchLabel,
  formatForecastBatchTitle,
  getForecastSourceLabel,
} from "./forecastMetadata";

describe("forecast metadata formatting", () => {
  it("formats batch title as metric + issued date", () => {
    const batch: ForecastBatch = {
      id: "forecast-iri-2025-10",
      source: "iri",
      issuedDate: "2025-10",
      targetDates: ["2025-11", "2025-12"],
      data: [{ nino34: 0.2 }, { nino34: 0.3 }],
      isHistorical: false,
    };

    expect(formatForecastBatchTitle(batch)).toBe("Niño 3.4 2025-10发布");
  });

  it("extracts multiple metrics from one batch in stable order", () => {
    const batch: ForecastBatch = {
      id: "forecast-mixed-2025-10",
      source: "iri",
      issuedDate: "2025-10",
      targetDates: ["2025-11"],
      data: [{ dmi: 0.6, nino34: 0.4 }],
      isHistorical: false,
    };

    expect(extractForecastMetrics(batch)).toEqual(["nino34", "dmi"]);
    expect(formatForecastBatchTitle(batch)).toBe("Niño 3.4 / DMI 2025-10发布");
  });

  it("maps source labels with fallback", () => {
    expect(getForecastSourceLabel({ id: "forecast-jamstec-2025-10" } as ForecastBatch)).toBe("JAMSTEC");
    expect(getForecastSourceLabel({ id: "forecast-iri-2025-10" } as ForecastBatch)).toBe("IRI");
    expect(getForecastSourceLabel({ id: "forecast-other-2025-10", source: "custom" } as ForecastBatch)).toBe(
      "CUSTOM",
    );
  });

  it("finds latest batch for a specific metric", () => {
    const forecasts: ForecastBatch[] = [
      {
        id: "forecast-jamstec-2024-12",
        source: "jamstec",
        issuedDate: "2024-12",
        targetDates: ["2025-01"],
        data: [{ nino34: 0.1 }],
        isHistorical: true,
      },
      {
        id: "forecast-jamstec-2025-12",
        source: "jamstec",
        issuedDate: "2025-12",
        targetDates: ["2026-01"],
        data: [{ dmi: 0.5 }],
        isHistorical: false,
      },
      {
        id: "forecast-iri-2025-11",
        source: "iri",
        issuedDate: "2025-11",
        targetDates: ["2025-12"],
        data: [{ nino34: 0.4 }],
        isHistorical: false,
      },
    ];

    const selected = findLatestForecastForMetric(forecasts, "nino34");
    expect(selected?.id).toBe("forecast-iri-2025-11");
  });

  it("formats selector label as source + issued batch only", () => {
    const batch: ForecastBatch = {
      id: "forecast-iri-2025-11",
      source: "iri",
      issuedDate: "2025-11",
      targetDates: ["2025-12"],
      data: [{ nino34: 0.3 }],
      isHistorical: false,
    };

    expect(formatForecastBatchLabel(batch)).toBe("2025-11批次");
    expect(formatForecastBatchLabel(batch, "en")).toBe("2025-11 batch");
    expect(formatForecastBatchTitle(batch, "en")).toBe("Niño 3.4 · 2025-11 release");
  });

  it("extracts unique issue months in descending order", () => {
    const forecasts: ForecastBatch[] = [
      {
        id: "forecast-iri-2025-11",
        source: "iri",
        issuedDate: "2025-11",
        targetDates: ["2025-12"],
        data: [{ nino34: 0.4 }],
        isHistorical: false,
      },
      {
        id: "forecast-jamstec-2025-11",
        source: "jamstec",
        issuedDate: "2025-11",
        targetDates: ["2025-12"],
        data: [{ dmi: 0.3 }],
        isHistorical: false,
      },
      {
        id: "forecast-iri-2025-10",
        source: "iri",
        issuedDate: "2025-10",
        targetDates: ["2025-11"],
        data: [{ nino34: 0.2 }],
        isHistorical: true,
      },
    ];

    expect(getForecastIssueMonths(forecasts)).toEqual(["2025-11", "2025-10"]);
  });

  it("builds a merged monthly batch from multi-source inputs", () => {
    const forecasts: ForecastBatch[] = [
      {
        id: "forecast-iri-2025-11",
        source: "iri",
        issuedDate: "2025-11",
        targetDates: ["2025-12", "2026-01"],
        data: [{ nino34: 0.4 }, { nino34: 0.5 }],
        isHistorical: false,
      },
      {
        id: "forecast-jamstec-2025-11",
        source: "jamstec",
        issuedDate: "2025-11",
        targetDates: ["2025-12", "2026-01"],
        data: [{ dmi: 0.1 }, { dmi: 0.2 }],
        isHistorical: false,
      },
    ];

    const merged = buildMonthlyForecastBatch(forecasts, "2025-11");
    expect(merged?.issuedDate).toBe("2025-11");
    expect(merged?.targetDates).toEqual(["2025-12", "2026-01"]);
    expect(merged?.data[0]).toMatchObject({ nino34: 0.4, dmi: 0.1 });
    expect(merged?.data[1]).toMatchObject({ nino34: 0.5, dmi: 0.2 });
  });
});
