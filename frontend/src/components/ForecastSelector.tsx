import React, { useState, useRef, useEffect, useMemo } from 'react';
import { ForecastBatch } from '../types/enso';
import { getForecastIssueMonths } from '../utils/forecastMetadata';
import type { Language } from '../i18n';
import { getI18n } from '../i18n';

interface ForecastSelectorProps {
  forecasts: ForecastBatch[];
  selectedForecast: ForecastBatch | null;
  onSelect: (issuedDate: string | null) => void;
  language: Language;
}

export const ForecastSelector: React.FC<ForecastSelectorProps> = ({
  forecasts,
  selectedForecast,
  onSelect,
  language,
}) => {
  const t = getI18n(language);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const issueMonths = useMemo(() => getForecastIssueMonths(forecasts), [forecasts]);

  const formatIssueMonthLabel = (issueMonth: string) =>
    language === "en" ? `${issueMonth} ${t.batchWord}` : `${issueMonth}${t.batchWord}`;

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getDisplayText = () => {
    if (selectedForecast === null) {
      return t.forecastSelectorDefaultLabel;
    }
    return `${formatIssueMonthLabel(selectedForecast.issuedDate)}${
      selectedForecast.issuedDate === issueMonths[0] ? t.forecastSelectorLatestSuffix : ''
    }`;
  };

  return (
    <div className="panel-subtle fade-in">
      <div className="flex items-center justify-between mb-2">
        <h3 className="panel-title">{t.forecastSelectorTitle}</h3>
        <span className="panel-meta">{t.forecastSelectorBatchCount(issueMonths.length)}</span>
      </div>
      
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full px-4 py-2 bg-white border border-[var(--panel-border)] rounded-lg text-left flex items-center justify-between hover:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-soft)] focus:border-transparent"
        >
          <span className="text-sm text-[var(--ink-1)]">{getDisplayText()}</span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {isOpen && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-[var(--panel-border)] rounded-lg shadow-lg max-h-60 overflow-auto">
            <div
              onClick={() => {
                onSelect(null);
                setIsOpen(false);
              }}
              className={`px-4 py-2 cursor-pointer hover:bg-gray-100 text-sm ${
                selectedForecast === null ? 'bg-[var(--accent-soft)] text-[var(--accent)] font-medium' : 'text-[var(--ink-1)]'
              }`}
            >
              {t.forecastSelectorDefaultLabel}
            </div>
            
            <div className="border-t border-gray-100"></div>
            
            {issueMonths.map((issueMonth, index) => (
              <div
                key={issueMonth}
                onClick={() => {
                  onSelect(issueMonth);
                  setIsOpen(false);
                }}
                className={`px-4 py-2 cursor-pointer hover:bg-gray-100 text-sm flex items-center justify-between ${
                  selectedForecast?.issuedDate === issueMonth
                    ? 'bg-[var(--accent-soft)] text-[var(--accent)] font-medium'
                    : 'text-[var(--ink-1)]'
                }`}
              >
                <span>{formatIssueMonthLabel(issueMonth)}</span>
                <div className="flex items-center gap-1">
                  {index === 0 && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                      {t.forecastSelectorLatestBadge}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <p className="mt-2 text-xs text-[var(--ink-muted)] text-right">
        {t.forecastSelectorHint}
      </p>
    </div>
  );
};
