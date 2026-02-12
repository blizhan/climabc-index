import { useState, useEffect } from 'react';
import { DataSet } from '../types/enso';
import { loadDataFromParquetAPI, generateMockData } from '../utils/dataLoader';
import { buildMonthlyForecastBatch } from '../utils/forecastMetadata';

// Set to true only for explicit local mock-data development.
const USE_MOCK_DATA = false;

export function useENSOData() {
  const [data, setData] = useState<DataSet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);

        let loadedData: DataSet;
        if (USE_MOCK_DATA) {
          // Fallback to mock data for development
          loadedData = generateMockData();
        } else {
          // Load from parquet-backed local API.
          loadedData = await loadDataFromParquetAPI();
        }

        setData(loadedData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const selectForecast = (issuedDate: string | null) => {
    if (!data) return;
    
    if (issuedDate === null) {
      setData({ ...data, selectedForecast: null });
    } else {
      const selected = buildMonthlyForecastBatch(data.forecasts, issuedDate);
      setData({ ...data, selectedForecast: selected });
    }
  };

  return { 
    data, 
    loading, 
    error,
    selectForecast,
  };
}
