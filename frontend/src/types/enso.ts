export type MetricKey =
  | 'nino34'
  | 'nino12'
  | 'nino3'
  | 'nino4'
  | 'soi'
  | 'oni'
  | 'dmi'
  | 'tni'
  | 'censo'
  | 'ao'
  | 'pdo'
  | 'wp'
  | 'amo_us'
  | 'amo_sm'
  | 'dmiwest'
  | 'dmieast'
  | 'nao'
  | 'np'
  | 'tpi'
  | 'glbts'
  | 'glbtssst';

export type ENSOValues = Partial<Record<MetricKey, number>>;

export interface ENSODataPoint extends ENSOValues {
  date: string;
}

export interface ForecastBatch {
  id: string;
  source?: string;
  issuedDate: string;      // 预报发布日期
  targetDates: string[];   // 预报目标日期
  data: ENSOValues[];
  isHistorical: boolean;   // 是否已成为历史（有真实值对比）
}

export interface HistoricalForecast {
  batchId: string;
  issuedDate: string;
  metric: MetricKey;
  targetDate: string;
  forecastValue: number;
  actualValue?: number;    // 如果已发生，真实值
  error?: number;          // 预报误差
}

export interface DataSet {
  observations: ENSODataPoint[];           // 历史观测值
  forecasts: ForecastBatch[];              // 所有预报批次
  latestForecast: ForecastBatch | null;    // 最新预报
  selectedForecast: ForecastBatch | null;  // 用户选择的预报批次
}

export interface MetricConfig {
  key: MetricKey;
  label: string;
  unit: string;
  color: string;
  yAxisIndex: number;
  updateFrequency: 'monthly' | 'weekly' | 'daily';
}

export const METRICS: MetricConfig[] = [
  { key: 'nino34', label: 'Niño 3.4', unit: '°C', color: '#5470c6', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'nino12', label: 'Niño 1+2', unit: '°C', color: '#91cc75', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'nino3', label: 'Niño 3', unit: '°C', color: '#fac858', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'nino4', label: 'Niño 4', unit: '°C', color: '#ee6666', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'soi', label: 'SOI', unit: 'hPa', color: '#73c0de', yAxisIndex: 1, updateFrequency: 'weekly' },
  { key: 'oni', label: 'ONI', unit: '°C', color: '#3ba272', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'dmi', label: 'DMI', unit: '°C', color: '#9a60b4', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'tni', label: 'TNI', unit: 'index', color: '#f08c00', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'censo', label: 'CENSO', unit: 'index', color: '#f76707', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'ao', label: 'AO', unit: 'index', color: '#2f9e44', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'pdo', label: 'PDO', unit: 'index', color: '#1971c2', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'wp', label: 'WP', unit: 'hPa', color: '#0c8599', yAxisIndex: 1, updateFrequency: 'monthly' },
  { key: 'amo_us', label: 'AMO (Raw)', unit: '°C', color: '#d6336c', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'amo_sm', label: 'AMO (Smoothed)', unit: '°C', color: '#a61e4d', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'dmiwest', label: 'DMI West', unit: '°C', color: '#5f3dc4', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'dmieast', label: 'DMI East', unit: '°C', color: '#7048e8', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'nao', label: 'NAO', unit: 'hPa', color: '#228be6', yAxisIndex: 1, updateFrequency: 'monthly' },
  { key: 'np', label: 'NP', unit: 'hPa', color: '#15aabf', yAxisIndex: 1, updateFrequency: 'monthly' },
  { key: 'tpi', label: 'TPI', unit: '°C', color: '#e8590c', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'glbts', label: 'GLBTS', unit: '°C', color: '#c2255c', yAxisIndex: 0, updateFrequency: 'monthly' },
  { key: 'glbtssst', label: 'GLBTSSST', unit: '°C', color: '#862e9c', yAxisIndex: 0, updateFrequency: 'monthly' },
];

export type ExportFormat = 'csv' | 'json' | 'png';
