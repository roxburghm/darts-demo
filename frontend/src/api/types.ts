export interface UploadInitRequest {
  filename: string
  file_size: number
  chunk_size?: number
  file_type?: 'csv' | 'parquet'
}

export interface UploadInitResponse {
  session_id: string
  upload_id: string
  total_chunks: number
}

export interface UploadStatusResponse {
  upload_id: string
  status: 'uploading' | 'parsing' | 'ready' | 'error'
  chunks_received: number
  total_chunks: number
  parsing_progress: number
  error: string | null
}

export interface ColumnInfo {
  name: string
  dtype: string
  null_count: number
  null_pct: number
  sample_values: (string | number | null)[]
}

export interface KPIDefinition {
  name: string
  formula: string
  description: string
}

export interface DatasetMetadata {
  session_id: string
  filename: string
  row_count: number
  time_range: [string, string]
  timestamp_column: string
  dimension_columns: ColumnInfo[]
  metric_columns: ColumnInfo[]
  skipped_header_lines: number
  kpi_definitions?: KPIDefinition[]
}

export interface DimensionValues {
  column: string
  values: string[]
  count: number
}

export type AggregationLevel = 'raw' | '15min' | '30min' | '1h' | '4h' | '1d'


// --- Model Registry ---

export interface ModelParam {
  name: string
  label: string
  type: 'int' | 'float' | 'bool' | 'select'
  default: number | boolean | string
  min?: number
  max?: number
  step?: number
  options?: string[]
  description: string
}

export interface ModelInfo {
  id: string
  name: string
  description: string
  category: 'scorer' | 'forecast'
  supports_multivariate: boolean
  min_data_points: number
  requires_seasonality: boolean
  requires_dimensions: boolean
  gpu_accelerated: boolean
  foundation: boolean
  params: ModelParam[]
}

export interface ModelCompatibility {
  model_id: string
  compatible: boolean
  reason: string | null
}

export interface CompatibilityResponse {
  models: ModelCompatibility[]
}


// --- Detection Config ---

export type TransformId = 'winsorize' | 'log' | 'boxcox' | 'diff' | 'scale_standard' | 'scale_minmax'
export type InfillMethod = 'none' | 'linear' | 'time' | 'ffill' | 'zero'

export interface DartsDetectionConfig {
  model_id: string
  metrics: string[]
  dimensions?: string[] | null
  dimension_filters?: Record<string, string[]> | null
  aggregation: AggregationLevel
  params: Record<string, number | boolean | string>
  detector_type: 'quantile' | 'threshold' | 'iqr'
  detector_threshold: number
  smoothing_window: number
  transforms: TransformId[]
  infill: InfillMethod
  scorer_id: string
  random_seed: number | null
  // Anomaly filtering
  persistence_damping: number
  min_anomaly_points: number
  volume_gate_metric: string | null
  volume_gate_threshold: number
}


// --- Results ---

export interface DartsAnomalyPoint {
  timestamp: string
  metric: string
  value: number
  score: number
  is_anomaly: boolean
  severity: 'low' | 'medium' | 'high'
  dimension_values?: Record<string, string> | null
}

export interface ForecastPoint {
  timestamp: string
  metric: string
  predicted: number
  actual: number
  dimension_values?: Record<string, string> | null
}

export interface AnomalyRegion {
  start: string
  end: string
  metric: string
  severity: 'low' | 'medium' | 'high'
  avg_score: number
  point_count: number
  dimension_values?: Record<string, string> | null
}

export interface AnomalySummary {
  total_points_analyzed: number
  total_anomalies: number
  total_regions: number
  by_severity: Record<string, number>
  by_metric: Record<string, number>
}

export interface DartsAnomalyResult {
  run_id: string
  config: DartsDetectionConfig
  anomalies: DartsAnomalyPoint[]
  scores: Array<{ timestamp: string; metric: string; score: number }>
  forecast: ForecastPoint[] | null
  summary: AnomalySummary
  regions: AnomalyRegion[]
}


// --- Visualization ---

export interface SeriesData {
  name: string
  timestamps: string[]
  values: (number | null)[]
}

export interface TimeSeriesRequest {
  metrics: string[]
  dimensions?: string[] | null
  dimension_filters?: Record<string, string[]> | null
  aggregation: AggregationLevel
  time_start?: string | null
  time_end?: string | null
  max_points?: number
  smoothing_window?: number
  transforms?: TransformId[]
  infill?: InfillMethod
}

export interface TimeSeriesResponse {
  series: SeriesData[]
  original_series?: SeriesData[] | null
  total_raw_points: number
  downsampled: boolean
}

export interface WebSocketMessage {
  type: 'progress' | 'complete' | 'error' | 'ping'
  stage?: string
  progress?: number
  detail?: string
  run_id?: string
}
