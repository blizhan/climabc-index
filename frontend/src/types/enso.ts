export interface ENSODataPoint {
  date: string;
  nino34: number;
  nino12: number;
  nino3: number;
  nino4: number;
  soi: number;
  oni: number;
  dmi?: number;
}

export interface ForecastBatch {
  id: string;
  source?: string;
  issuedDate: string;      // 预报发布日期
  targetDates: string[];   // 预报目标日期
  data: Partial<ENSODataPoint>[];
  isHistorical: boolean;   // 是否已成为历史（有真实值对比）
}

export interface HistoricalForecast {
  batchId: string;
  issuedDate: string;
  metric: keyof ENSODataPoint;
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
  key: keyof ENSODataPoint;
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
];

export type ExportFormat = 'csv' | 'json' | 'png';
