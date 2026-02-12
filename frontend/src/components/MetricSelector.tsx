import React from 'react';
import { METRICS } from '../types/enso';
import type { Language } from '../i18n';
import { getI18n } from '../i18n';

interface MetricSelectorProps {
  selectedMetrics: string[];
  onChange: (metrics: string[]) => void;
  language: Language;
}

export const MetricSelector: React.FC<MetricSelectorProps> = ({
  selectedMetrics,
  onChange,
  language,
}) => {
  const t = getI18n(language);

  const toggleMetric = (key: string) => {
    if (selectedMetrics.includes(key)) {
      onChange(selectedMetrics.filter((m) => m !== key));
    } else {
      onChange([...selectedMetrics, key]);
    }
  };

  return (
    <div className="panel-subtle fade-in">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="panel-title">{t.metricSelectorTitle}</h3>
        <span className="panel-meta">{t.metricSelectorSelectedCount(selectedMetrics.length)}</span>
      </div>
      <div className="metric-chip-grid">
        {METRICS.map((metric) => (
          <button
            key={metric.key}
            onClick={() => toggleMetric(metric.key)}
            className={`metric-chip ${
              selectedMetrics.includes(metric.key)
                ? 'metric-chip-active'
                : 'metric-chip-inactive'
            }`}
            style={
              selectedMetrics.includes(metric.key)
                ? {
                  background: `linear-gradient(135deg, ${metric.color} 0%, ${metric.color} 100%)`,
                }
                : {}
            }
          >
            {metric.label}
          </button>
        ))}
      </div>
    </div>
  );
};
