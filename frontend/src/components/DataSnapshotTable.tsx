import React, { useMemo, useState } from "react";
import type { ENSODataPoint, ForecastBatch } from "../types/enso";
import { METRICS } from "../types/enso";
import { formatForecastBatchLabel, formatForecastBatchTitle } from "../utils/forecastMetadata";
import { buildDataSnapshotRows } from "../utils/tableData";
import type { Language } from "../i18n";
import { getI18n } from "../i18n";

interface DataSnapshotTableProps {
  observations: ENSODataPoint[];
  forecasts: ForecastBatch[];
  selectedForecast: ForecastBatch | null;
  selectedMetrics: string[];
  language: Language;
}

export const DataSnapshotTable: React.FC<DataSnapshotTableProps> = ({
  observations,
  forecasts,
  selectedForecast,
  selectedMetrics,
  language,
}) => {
  const t = getI18n(language);
  const [expanded, setExpanded] = useState(false);
  const metricConfigs = useMemo(
    () => METRICS.filter((metric) => selectedMetrics.includes(metric.key)),
    [selectedMetrics],
  );

  const rows = useMemo(
    () =>
      buildDataSnapshotRows(
        observations,
        forecasts,
        selectedForecast,
        metricConfigs.map((metric) => metric.key),
      ),
    [forecasts, metricConfigs, observations, selectedForecast],
  );

  const activeForecastText = selectedForecast
    ? `${formatForecastBatchLabel(selectedForecast, language)} · ${formatForecastBatchTitle(selectedForecast, language)}`
    : t.snapshotDefaultBatchText;

  return (
    <section className="panel fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="panel-title">{t.snapshotTitle}</h3>
          <p className="panel-subtitle">{t.snapshotSubtitle}</p>
          <p className="panel-meta mt-1">{t.snapshotCurrentBatchPrefix}{activeForecastText}</p>
        </div>
        <button
          onClick={() => setExpanded((value) => !value)}
          className="panel-toggle-btn"
          type="button"
        >
          {expanded ? t.snapshotCollapse : t.snapshotExpand}
        </button>
      </div>

      {expanded && (
        <div className="mt-4 overflow-x-auto">
          <table className="data-grid">
            <thead>
              <tr>
                <th>{t.snapshotDateHeader}</th>
                <th>{t.snapshotTypeHeader}</th>
                {metricConfigs.map((metric) => (
                  <th key={metric.key}>{metric.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.rowType}-${row.date}`}>
                  <td className="mono-text">{row.date}</td>
                  <td>
                    <span className={`row-tag ${row.rowType === "forecast" ? "row-tag-forecast" : "row-tag-observation"}`}>
                      {row.rowType === "forecast" ? t.snapshotTypeForecast : t.snapshotTypeObservation}
                    </span>
                  </td>
                  {metricConfigs.map((metric) => (
                    <td key={`${row.rowType}-${row.date}-${metric.key}`}>
                      {typeof row.values[metric.key] === "number"
                        ? row.values[metric.key]?.toFixed(2)
                        : "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};
