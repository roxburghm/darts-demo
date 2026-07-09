export const AGGREGATION_OPTIONS = [
  { value: 'raw', label: 'Raw (5 min)' },
  { value: '15min', label: '15 Minutes' },
  { value: '30min', label: '30 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: '1 Day' },
] as const

export const ALGORITHM_OPTIONS = [
  { value: 'mstl_zscore', label: 'Seasonal Decomposition', description: 'Best for single metrics with daily/weekly patterns' },
  { value: 'isolation_forest', label: 'Isolation Forest', description: 'Best for detecting anomalies across multiple correlated metrics' },
  { value: 'combined', label: 'Combined (Ensemble)', description: 'Uses both methods for comprehensive detection' },
] as const

export const CHUNK_SIZE = 2 * 1024 * 1024 // 2MB
export const MAX_CHART_POINTS = 3000
