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
          <div>
            <div className="hero-heading">
              <h1 className="hero-title">{t.heroTitle}</h1>
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
            <p className="hero-subtitle">{t.heroSubtitle}</p>
          </div>
          <div className="kpi-grid">
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
        </section>

        <section className="control-grid">
          <div className="control-grid-left">
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
          <h3 className="panel-title">{t.sourceLinksTitle}</h3>
          <ul className="source-list">
            <li>
              <a
                href="https://psl.noaa.gov/data/climateindices/list/"
                target="_blank"
                rel="noreferrer"
              >
                {t.sourcePslLabel}
              </a>
            </li>
            <li>
              <a
                href="https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/?enso_tab=enso-sst_table"
                target="_blank"
                rel="noreferrer"
              >
                {t.sourceIriLabel}
              </a>
            </li>
            <li>
              <a
                href="https://www.jamstec.go.jp/virtualearth/data/SINTEX/SINTEX_DMI.csv"
                target="_blank"
                rel="noreferrer"
              >
                {t.sourceJamstecLabel}
              </a>
            </li>
          </ul>
          <p className="panel-meta mt-3">
            {t.sourceUpdateNote}
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;
