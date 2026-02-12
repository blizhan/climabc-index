import React from 'react';
import { ENSODataPoint, ExportFormat } from '../types/enso';
import { exportToCSV, exportToJSON } from '../utils/dataLoader';
import type { Language } from '../i18n';
import { getI18n } from '../i18n';

interface ExportPanelProps {
  data: ENSODataPoint[];
  chartInstance: any;
  language: Language;
}

export const ExportPanel: React.FC<ExportPanelProps> = ({ data, chartInstance, language }) => {
  const t = getI18n(language);

  const handleExport = (format: ExportFormat) => {
    const timestamp = new Date().toISOString().slice(0, 10);
    
    switch (format) {
      case 'csv':
        exportToCSV(data, `enso-data-${timestamp}.csv`);
        break;
      case 'json':
        exportToJSON(data, `enso-data-${timestamp}.json`);
        break;
      case 'png':
        if (chartInstance) {
          const url = chartInstance.getDataURL({
            type: 'png',
            pixelRatio: 2,
            backgroundColor: '#fff',
          });
          const link = document.createElement('a');
          link.download = `enso-chart-${timestamp}.png`;
          link.href = url;
          link.click();
        }
        break;
    }
  };

  return (
    <div className="panel-subtle fade-in">
      <div className="mb-3">
        <h3 className="panel-title inline">{t.exportPanelTitle}</h3>
        <span className="panel-subtitle" style={{ marginLeft: '0.5rem' }}>{t.exportPanelSubtitle}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => handleExport('csv')}
          className="action-btn action-btn-primary"
        >
          {t.exportCsv}
        </button>
        <button
          onClick={() => handleExport('json')}
          className="action-btn action-btn-secondary"
        >
          {t.exportJson}
        </button>
        <button
          onClick={() => handleExport('png')}
          className="action-btn action-btn-neutral"
        >
          {t.exportPng}
        </button>
      </div>
    </div>
  );
};
