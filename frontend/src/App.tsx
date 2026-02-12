import React, { useRef } from 'react';
import { TimelineChart, TimelineChartRef } from './components/TimelineChart';
import { MetricSelector } from './components/MetricSelector';
import { ForecastSelector } from './components/ForecastSelector';
import { ExportPanel } from './components/ExportPanel';
import { DataSnapshotTable } from './components/DataSnapshotTable';
import { useENSOData } from './hooks/useENSOData';
import type { Language } from './i18n';
import { getI18n } from './i18n';

const DEFAULT_SELECTED_METRICS = ['nino34', 'nino12', 'oni', 'soi'];

function App() {
  const [language, setLanguage] = React.useState<Language>('zh');
  const t = getI18n(language);
  const { data, loading, error, selectForecast } = useENSOData();
  const [selectedMetrics, setSelectedMetrics] = React.useState<string[]>(
    DEFAULT_SELECTED_METRICS
  );
  const chartRef = useRef<TimelineChartRef>(null);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg text-gray-600">{t.loadingData}</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg text-red-600">{t.errorPrefix}: {error || t.errorLoadFailed}</div>
      </div>
    );
  }

  const latestObservationDate = data.observations.length
    ? data.observations[data.observations.length - 1].date
    : 'N/A';
  const sourceCount = new Set(data.forecasts.map((batch) => batch.source?.toLowerCase() || 'unknown')).size;

  return (
    <div className="app-shell">
      <div className="app-container">
        <section className="hero-card fade-in">
          <div className="hero-heading">
            <h1 className="hero-title">{t.heroTitle}</h1>
            <div className="flex items-center gap-3">
              <a
                href="https://github.com/blizhan/climabc-index"
                target="_blank"
                rel="noopener noreferrer"
                className="github-link"
                aria-label="View on GitHub"
                title={language === 'zh' ? '在 GitHub 上查看' : 'View on GitHub'}
              >
                <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
              </a>
              <div className="lang-switch" role="group" aria-label={t.languageLabel}>
                <button
                  type="button"
                  className={language === 'zh' ? 'active' : ''}
                  onClick={() => setLanguage('zh')}
                >
                  {t.languageZh}
                </button>
                <button
                  type="button"
                  className={language === 'en' ? 'active' : ''}
                  onClick={() => setLanguage('en')}
                >
                  {t.languageEn}
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="control-grid">
          <div className="control-grid-left">
            <div className="kpi-grid-compact">
              <div className="kpi-card">
                <span className="kpi-label">{t.kpiObservations}</span>
                <strong className="kpi-value">{data.observations.length}</strong>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">{t.kpiForecastBatches}</span>
                <strong className="kpi-value">{data.forecasts.length}</strong>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">{t.kpiLatestObservation}</span>
                <strong className="kpi-value mono-text">{latestObservationDate}</strong>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">{t.kpiForecastSourceCount}</span>
                <strong className="kpi-value">{sourceCount}</strong>
              </div>
            </div>
            <ExportPanel 
              data={data.observations} 
              chartInstance={chartRef.current?.getChartInstance()} 
              language={language}
            />
            <ForecastSelector
              forecasts={data.forecasts}
              selectedForecast={data.selectedForecast}
              onSelect={selectForecast}
              language={language}
            />
          </div>
          <MetricSelector
            selectedMetrics={selectedMetrics}
            onChange={setSelectedMetrics}
            language={language}
          />
        </section>

        <section className="panel fade-in mt-4">
          <h3 className="panel-title mb-2">{t.timelineViewTitle}</h3>
          <p className="panel-subtitle mb-4">{t.timelineViewSubtitle}</p>
          <TimelineChart 
            ref={chartRef}
            observations={data.observations}
            forecasts={data.forecasts}
            selectedForecast={data.selectedForecast}
            selectedMetrics={selectedMetrics}
            language={language}
          />
        </section>

        <section className="mt-4">
          <DataSnapshotTable
            observations={data.observations}
            forecasts={data.forecasts}
            selectedForecast={data.selectedForecast}
            selectedMetrics={selectedMetrics}
            language={language}
          />
        </section>

        <div className="panel mt-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-4 flex-wrap">
              <span className="text-sm font-semibold text-[var(--ink-2)]">{t.sourceLinksTitle}:</span>
              <a
                href="https://psl.noaa.gov/data/climateindices/list/"
                target="_blank"
                rel="noreferrer"
                className="source-link"
              >
                {t.sourcePslLabel}
              </a>
              <a
                href="https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/?enso_tab=enso-sst_table"
                target="_blank"
                rel="noreferrer"
                className="source-link"
              >
                {t.sourceIriLabel}
              </a>
              <a
                href="https://www.jamstec.go.jp/virtualearth/data/SINTEX/SINTEX_DMI.csv"
                target="_blank"
                rel="noreferrer"
                className="source-link"
              >
                {t.sourceJamstecLabel}
              </a>
            </div>
            <span className="text-xs text-[var(--ink-muted)]">{t.sourceUpdateNote}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
