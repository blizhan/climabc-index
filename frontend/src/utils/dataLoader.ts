import { ENSODataPoint, ENSOValues, ForecastBatch, DataSet, METRICS } from '../types/enso';
import { loadDatasetFromParquet } from './parquetData';

const DATA_BASE_URL = (import.meta.env.VITE_DATA_BASE_URL || '').trim();

export async function loadDataFromParquetAPI(): Promise<DataSet> {
  return loadDatasetFromParquet({
    explicitBaseUrl: DATA_BASE_URL,
  });
}

// Fallback mock data generator (for development without data file)
export function generateMockData(): DataSet {
  const observations: ENSODataPoint[] = [];
  const forecasts: ForecastBatch[] = [];

  const startDate = new Date('1980-01-01');
  const endDate = new Date('2024-01-01');
  const now = new Date();

  // Generate observations (historical data)
  for (let d = new Date(startDate); d <= endDate; d.setMonth(d.getMonth() + 1)) {
    const dateStr = d.toISOString().slice(0, 7);
    const t = d.getTime() / (1000 * 60 * 60 * 24 * 365);

    observations.push({
      date: dateStr,
      nino34: Math.sin(t * 2) * 1.5 + (Math.random() - 0.5) * 0.5,
      nino12: Math.sin(t * 2 + 0.5) * 2 + (Math.random() - 0.5) * 0.6,
      nino3: Math.sin(t * 2 + 0.3) * 1.8 + (Math.random() - 0.5) * 0.5,
      nino4: Math.sin(t * 2 + 0.7) * 1.2 + (Math.random() - 0.5) * 0.4,
      soi: Math.cos(t * 2) * 10 + (Math.random() - 0.5) * 3,
      oni: Math.sin(t * 2) * 1.2 + (Math.random() - 0.5) * 0.4,
    });
  }

  // Generate forecast batches (monthly forecasts for past 12 months)
  for (let i = 0; i < 12; i++) {
    const issueDate = new Date(now);
    issueDate.setMonth(issueDate.getMonth() - i);
    const issueDateStr = issueDate.toISOString().slice(0, 7);

    const targetDates: string[] = [];
    const forecastData: ENSOValues[] = [];

    // Forecast for next 12 months from issue date
    for (let j = 1; j <= 12; j++) {
      const targetDate = new Date(issueDate);
      targetDate.setMonth(targetDate.getMonth() + j);
      const targetDateStr = targetDate.toISOString().slice(0, 7);
      targetDates.push(targetDateStr);

      const t = targetDate.getTime() / (1000 * 60 * 60 * 24 * 365);
      const baseValue = Math.sin(t * 2) * 1.5;

      // Add forecast error that increases with lead time
      const leadTimeError = (j / 12) * 0.5;

      forecastData.push({
        nino34: baseValue + (Math.random() - 0.5) * leadTimeError,
        nino12: Math.sin(t * 2 + 0.5) * 2 + (Math.random() - 0.5) * leadTimeError,
        nino3: Math.sin(t * 2 + 0.3) * 1.8 + (Math.random() - 0.5) * leadTimeError,
        nino4: Math.sin(t * 2 + 0.7) * 1.2 + (Math.random() - 0.5) * leadTimeError,
        soi: Math.cos(t * 2) * 10 + (Math.random() - 0.5) * leadTimeError * 5,
        oni: Math.sin(t * 2) * 1.2 + (Math.random() - 0.5) * leadTimeError,
      });
    }

    forecasts.push({
      id: `forecast-${issueDateStr}`,
      issuedDate: issueDateStr,
      targetDates,
      data: forecastData,
      isHistorical: i > 0, // All except the latest are historical
    });
  }

  return {
    observations,
    forecasts,
    latestForecast: forecasts[0] || null,
    selectedForecast: null,
  };
}

export function exportToCSV(data: ENSODataPoint[], filename: string = 'enso-data.csv'): void {
  const metricKeys = METRICS.map((metric) => metric.key);
  const headers = ['date', ...metricKeys];
  const rows = data.map(row => [
    row.date,
    ...metricKeys.map((key) => row[key] ?? ''),
  ]);
  
  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  downloadFile(csvContent, filename, 'text/csv');
}

export function exportToJSON(data: ENSODataPoint[], filename: string = 'enso-data.json'): void {
  const jsonContent = JSON.stringify(data, null, 2);
  downloadFile(jsonContent, filename, 'application/json');
}

export function exportChartToPNG(chartInstance: any, filename: string = 'enso-chart.png'): void {
  if (chartInstance) {
    const url = chartInstance.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff',
    });
    
    const link = document.createElement('a');
    link.download = filename;
    link.href = url;
    link.click();
  }
}

function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
