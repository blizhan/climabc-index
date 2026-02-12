import { describe, expect, it } from "vitest";
import type { ENSODataPoint, ForecastBatch } from "../types/enso";
import { buildDataSnapshotRows } from "./tableData";

describe("data snapshot table rows", () => {
  it("combines recent observations and selected forecast batch", () => {
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

    const batch: ForecastBatch = {
      id: "forecast-iri-2025-10",
      source: "iri",
      issuedDate: "2025-10",
      targetDates: ["2025-11", "2025-12"],
      data: [{ nino34: 0.2 }, { nino34: 0.4 }],
      isHistorical: false,
    };

    const rows = buildDataSnapshotRows(observations, [batch], batch, ["nino34"], 2, 2);
    expect(rows).toHaveLength(4);
    expect(rows[0]).toMatchObject({ date: "2025-12", rowType: "forecast", issuedDate: "2025-10" });
    expect(rows[1]).toMatchObject({ date: "2025-11", rowType: "forecast", issuedDate: "2025-10" });
    expect(rows[2]).toMatchObject({ date: "2025-10", rowType: "observation", issuedDate: null });
    expect(rows[3]).toMatchObject({ date: "2025-09", rowType: "observation", issuedDate: null });
  });

  it("uses latest batch per selected metric when no batch is selected", () => {
    const observations: ENSODataPoint[] = [
      {
        date: "2025-10",
        nino34: -0.1,
        nino12: 0.0,
        nino3: -0.1,
        nino4: 0.0,
        soi: 0.4,
        oni: -0.1,
        dmi: 0.2,
      },
    ];

    const forecasts: ForecastBatch[] = [
      {
        id: "forecast-jamstec-2025-12",
        source: "jamstec",
        issuedDate: "2025-12",
        targetDates: ["2026-01"],
        data: [{ dmi: 0.6 }],
        isHistorical: false,
      },
      {
        id: "forecast-iri-2025-11",
        source: "iri",
        issuedDate: "2025-11",
        targetDates: ["2026-01"],
        data: [{ nino34: 0.3 }],
        isHistorical: false,
      },
    ];

    const rows = buildDataSnapshotRows(observations, forecasts, null, ["nino34", "dmi"], 1, 1);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      date: "2026-01",
      rowType: "forecast",
      values: {
        nino34: 0.3,
        dmi: 0.6,
      },
    });
  });
});
