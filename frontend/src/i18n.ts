export type Language = "zh" | "en";

export interface I18nStrings {
  languageLabel: string;
  languageZh: string;
  languageEn: string;
  loadingData: string;
  errorPrefix: string;
  errorLoadFailed: string;
  heroTitle: string;
  heroSubtitle: string;
  kpiObservations: string;
  kpiForecastBatches: string;
  kpiLatestObservation: string;
  kpiForecastSourceCount: string;
  timelineViewTitle: string;
  timelineViewSubtitle: string;
  timelineChartTitle: string;
  timelineLegendObservationSuffix: string;
  timelineLegendForecastSuffix: string;
  timelineLegendLatestForecastSuffix: string;
  timelineNowSeriesName: string;
  timelineNowLabel: string;
  timelineSstAxisLabel: string;
  timelineSoiAxisLabel: string;
  metricSelectorTitle: string;
  metricSelectorSelectedCount: (count: number) => string;
  forecastSelectorTitle: string;
  forecastSelectorBatchCount: (count: number) => string;
  forecastSelectorDefaultLabel: string;
  forecastSelectorLatestBadge: string;
  forecastSelectorLatestSuffix: string;
  forecastSelectorHint: string;
  batchWord: string;
  exportPanelTitle: string;
  exportPanelSubtitle: string;
  exportCsv: string;
  exportJson: string;
  exportPng: string;
  snapshotTitle: string;
  snapshotSubtitle: string;
  snapshotCurrentBatchPrefix: string;
  snapshotDefaultBatchText: string;
  snapshotExpand: string;
  snapshotCollapse: string;
  snapshotDateHeader: string;
  snapshotTypeHeader: string;
  snapshotTypeObservation: string;
  snapshotTypeForecast: string;
  sourceLinksTitle: string;
  sourcePslLabel: string;
  sourceIriLabel: string;
  sourceJamstecLabel: string;
  sourceUpdateNote: string;
}

const I18N_STRINGS: Record<Language, I18nStrings> = {
  zh: {
    languageLabel: "语言",
    languageZh: "中文",
    languageEn: "EN",
    loadingData: "加载气候指数数据中...",
    errorPrefix: "错误",
    errorLoadFailed: "无法加载数据",
    heroTitle: "Climate Index Console",
    heroSubtitle: "多源气候指数观测与预报对照",
    kpiObservations: "观测样本",
    kpiForecastBatches: "预报批次",
    kpiLatestObservation: "最近观测",
    kpiForecastSourceCount: "预报源数量",
    timelineViewTitle: "时间序列视图",
    timelineViewSubtitle: "实线代表观测，虚线代表预报；可按指标与批次联动筛选",
    timelineChartTitle: "气候指数观测与预报时间线",
    timelineLegendObservationSuffix: "观测",
    timelineLegendForecastSuffix: "预报",
    timelineLegendLatestForecastSuffix: "最新预报",
    timelineNowSeriesName: "当前时间",
    timelineNowLabel: "现在",
    timelineSstAxisLabel: "海温 (°C)",
    timelineSoiAxisLabel: "SOI (hPa)",
    metricSelectorTitle: "指数筛选",
    metricSelectorSelectedCount: (count: number) => `已选 ${count} 项`,
    forecastSelectorTitle: "预报批次",
    forecastSelectorBatchCount: (count: number) => `共 ${count} 个批次`,
    forecastSelectorDefaultLabel: "最新批次",
    forecastSelectorLatestBadge: "最新",
    forecastSelectorLatestSuffix: " (最新)",
    forecastSelectorHint: "选择批次可对比预报与观测值",
    batchWord: "批次",
    exportPanelTitle: "数据导出",
    exportPanelSubtitle: "支持观测数据和图表导出",
    exportCsv: "导出 CSV",
    exportJson: "导出 JSON",
    exportPng: "导出图表 PNG",
    snapshotTitle: "数据快照表",
    snapshotSubtitle: "用于快速核对观测值与所选预报批次",
    snapshotCurrentBatchPrefix: "当前批次：",
    snapshotDefaultBatchText: "最新批次",
    snapshotExpand: "展开表格",
    snapshotCollapse: "收起表格",
    snapshotDateHeader: "日期",
    snapshotTypeHeader: "类型",
    snapshotTypeObservation: "观测",
    snapshotTypeForecast: "预报",
    sourceLinksTitle: "数据源",
    sourcePslLabel: "© NOAA PSL",
    sourceIriLabel: "© IRI ENSO Quick Look",
    sourceJamstecLabel: "© JAMSTEC SINTEX-F",
    sourceUpdateNote: "更新频率：每周刷新",
  },
  en: {
    languageLabel: "Language",
    languageZh: "中文",
    languageEn: "EN",
    loadingData: "Loading...",
    errorPrefix: "Error",
    errorLoadFailed: "Failed to load data",
    heroTitle: "Climate Index Console",
    heroSubtitle: "Cross-source climate index observations and forecast comparison",
    kpiObservations: "Observations",
    kpiForecastBatches: "Forecasts",
    kpiLatestObservation: "Latest",
    kpiForecastSourceCount: "Sources",
    timelineViewTitle: "Timeline View",
    timelineViewSubtitle: "Solid lines: observations, dashed lines: forecasts",
    timelineChartTitle: "Climate Index Timeline",
    timelineLegendObservationSuffix: "Obs",
    timelineLegendForecastSuffix: "Fcst",
    timelineLegendLatestForecastSuffix: "Latest",
    timelineNowSeriesName: "Now",
    timelineNowLabel: "Now",
    timelineSstAxisLabel: "Temp (°C)",
    timelineSoiAxisLabel: "SOI (hPa)",
    metricSelectorTitle: "Metrics",
    metricSelectorSelectedCount: (count: number) => `${count} selected`,
    forecastSelectorTitle: "Forecast Batch",
    forecastSelectorBatchCount: (count: number) => `${count} batches`,
    forecastSelectorDefaultLabel: "Latest Forecast",
    forecastSelectorLatestBadge: "Latest",
    forecastSelectorLatestSuffix: " (Latest)",
    forecastSelectorHint: "Pick a batch to compare",
    batchWord: "batch",
    exportPanelTitle: "Export",
    exportPanelSubtitle: "Export data and chart snapshots",
    exportCsv: "Export CSV",
    exportJson: "Export JSON",
    exportPng: "Export PNG",
    snapshotTitle: "Data Snapshot",
    snapshotSubtitle: "Compare observations vs selected forecast",
    snapshotCurrentBatchPrefix: "Batch: ",
    snapshotDefaultBatchText: "Latest: latest per metric",
    snapshotExpand: "Expand",
    snapshotCollapse: "Collapse",
    snapshotDateHeader: "Date",
    snapshotTypeHeader: "Type",
    snapshotTypeObservation: "Obs",
    snapshotTypeForecast: "Fcst",
    sourceLinksTitle: "Data Sources",
    sourcePslLabel: "© NOAA PSL",
    sourceIriLabel: "© IRI ENSO Quick Look",
    sourceJamstecLabel: "© JAMSTEC SINTEX-F",
    sourceUpdateNote: "Updated weekly",
  },
};

export function getI18n(language: Language): I18nStrings {
  return I18N_STRINGS[language];
}
