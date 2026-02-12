import { useRef, useEffect, useMemo, forwardRef, useImperativeHandle } from 'react';
import * as echarts from 'echarts';
import { ENSODataPoint, METRICS, ForecastBatch } from '../types/enso';
import type { Language } from '../i18n';
import { getI18n } from '../i18n';
import {
  buildForecastSeriesData,
  buildObservationSeriesData,
  buildTimelineDates,
  buildTimelineZoomRange,
} from '../utils/timelineData';
import { findLatestForecastForMetric } from '../utils/forecastMetadata';

interface TimelineChartProps {
  observations: ENSODataPoint[];
  forecasts: ForecastBatch[];
  selectedForecast: ForecastBatch | null;
  selectedMetrics: string[];
  language: Language;
}

export interface TimelineChartRef {
  getChartInstance: () => echarts.ECharts | null;
}

export const TimelineChart = forwardRef<TimelineChartRef, TimelineChartProps>(({
  observations,
  forecasts,
  selectedForecast,
  selectedMetrics,
  language,
}, ref) => {
  const t = getI18n(language);
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const selectedMetricConfigs = useMemo(() => {
    return METRICS.filter((m) => selectedMetrics.includes(m.key));
  }, [selectedMetrics]);

  useImperativeHandle(ref, () => ({
    getChartInstance: () => chartInstance.current,
  }));

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current);

    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstance.current?.dispose();
    };
  }, []);

  useEffect(() => {
    if (!chartInstance.current || observations.length === 0) return;

    const dates = buildTimelineDates(observations, forecasts);
    const observationsByDate = new Map<string, ENSODataPoint>(
      observations.map((point) => [point.date, point]),
    );
    const now = new Date().toISOString().slice(0, 7);
    const nowIndex = dates.findIndex((d) => d >= now);
    const splitIndex = nowIndex >= 0 ? nowIndex : dates.length;
    const zoomRange = buildTimelineZoomRange(dates, selectedForecast, now);

    const series: echarts.SeriesOption[] = [];
    const observationLegendData: string[] = [];
    const forecastLegendData: string[] = [];

    // Add observation series (solid lines)
    selectedMetricConfigs.forEach((metric) => {
      const observationData = buildObservationSeriesData(dates, observations, metric.key);
      
      const observationSeriesName = `${metric.label} (${t.timelineLegendObservationSuffix})`;
      series.push({
        name: observationSeriesName,
        type: 'line',
        yAxisIndex: metric.yAxisIndex,
        data: observationData,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          type: 'solid',
        },
        itemStyle: {
          color: metric.color,
        },
        z: 10,
      });
      observationLegendData.push(observationSeriesName);

      // Add forecast series if selected
      if (selectedForecast) {
        const forecastData = buildForecastSeriesData(
          dates,
          selectedForecast,
          metric.key,
          observationsByDate,
        );

        if (!forecastData.some((value) => value !== null)) {
          return;
        }

        const forecastSeriesName = `${metric.label} (${t.timelineLegendForecastSuffix})`;
        series.push({
          name: forecastSeriesName,
          type: 'line',
          yAxisIndex: metric.yAxisIndex,
          data: forecastData,
          smooth: true,
          symbol: 'none',
          lineStyle: {
            width: 2,
            type: 'dashed',
          },
          itemStyle: {
            color: metric.color,
            opacity: 0.7,
          },
          z: 5,
        });
        forecastLegendData.push(forecastSeriesName);
      } else {
        // Default view: one latest forecast batch per selected metric.
        const latestMetricBatch = findLatestForecastForMetric(forecasts, metric.key);
        if (!latestMetricBatch) {
          return;
        }
        const forecastData = buildForecastSeriesData(
          dates,
          latestMetricBatch,
          metric.key,
          observationsByDate,
        );
        if (!forecastData.some((value) => value !== null)) {
          return;
        }
        const forecastSeriesName = `${metric.label} (${t.timelineLegendLatestForecastSuffix})`;
        series.push({
          name: forecastSeriesName,
          type: 'line',
          yAxisIndex: metric.yAxisIndex,
          data: forecastData,
          smooth: true,
          symbol: 'none',
          lineStyle: {
            width: 2,
            type: 'dashed',
          },
          itemStyle: {
            color: metric.color,
            opacity: 0.78,
          },
          z: 5,
        });
        forecastLegendData.push(forecastSeriesName);
      }
    });

    // Add vertical line to separate past and future
    if (splitIndex < dates.length) {
      series.push({
        name: t.timelineNowSeriesName,
        type: 'line',
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: {
            color: '#999',
            type: 'dotted',
            width: 2,
          },
          data: [
            {
              xAxis: splitIndex,
              label: {
                formatter: t.timelineNowLabel,
                position: 'end',
              },
            },
          ],
        },
      });
    }

    const legends: echarts.LegendComponentOption[] = [
      {
        data: observationLegendData,
        left: '3%',
        bottom: 5,
        width: '44%',
        type: 'scroll',
        textStyle: {
          color: '#475569',
          fontSize: 11,
        },
      },
    ];

    if (forecastLegendData.length > 0) {
      legends.push({
        data: forecastLegendData,
        right: '3%',
        bottom: 5,
        width: '44%',
        type: 'scroll',
        textStyle: {
          color: '#475569',
          fontSize: 11,
        },
      });
    }

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      title: {
        text: t.timelineChartTitle,
        left: 'center',
        textStyle: {
          color: '#1e293b',
          fontWeight: 700,
          fontFamily: 'Manrope, sans-serif',
          fontSize: 16,
        },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        borderColor: 'rgba(148, 163, 184, 0.4)',
        textStyle: {
          color: '#e2e8f0',
        },
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          
          let html = `<div style="font-weight:bold;margin-bottom:5px;">${params[0].axisValue}</div>`;
          
          params.forEach((param: any) => {
            if (param.value !== null && param.value !== undefined) {
              const color = param.color;
              html += `<div style="display:flex;align-items:center;margin:2px 0;">`;
              html += `<span style="display:inline-block;width:10px;height:10px;background:${color};margin-right:5px;border-radius:50%;"></span>`;
              html += `<span>${param.seriesName}: <strong>${param.value.toFixed(2)}</strong></span>`;
              html += `</div>`;
            }
          });
          
          return html;
        },
      },
      legend: legends,
      grid: {
        left: '3%',
        right: '4%',
        top: 68,
        bottom: '16%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLabel: {
          color: '#64748b',
          fontSize: 11,
        },
        axisLine: {
          lineStyle: {
            color: '#cbd5e1',
          },
        },
      },
      yAxis: [
        {
          type: 'value',
          name: t.timelineSstAxisLabel,
          position: 'left',
          nameTextStyle: {
            color: '#64748b',
          },
          axisLabel: {
            color: '#64748b',
          },
          axisLine: {
            show: true,
            lineStyle: {
              color: '#cbd5e1',
            },
          },
          splitLine: {
            lineStyle: {
              color: 'rgba(203, 213, 225, 0.45)',
            },
          },
        },
        {
          type: 'value',
          name: t.timelineSoiAxisLabel,
          position: 'right',
          nameTextStyle: {
            color: '#64748b',
          },
          axisLabel: {
            color: '#64748b',
          },
          axisLine: {
            show: true,
            lineStyle: {
              color: '#cbd5e1',
            },
          },
          splitLine: {
            show: false,
          },
        },
      ],
      dataZoom: [
        {
          type: 'inside',
          start: zoomRange.start,
          end: zoomRange.end,
        },
        {
          start: zoomRange.start,
          end: zoomRange.end,
          bottom: 40,
        },
      ],
      series,
    };

    chartInstance.current.setOption(option, true);
  }, [language, observations, forecasts, selectedForecast, selectedMetricConfigs]);

  return <div ref={chartRef} style={{ width: '100%', height: '540px' }} />;
});

TimelineChart.displayName = 'TimelineChart';
