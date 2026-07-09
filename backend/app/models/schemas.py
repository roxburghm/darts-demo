from pydantic import BaseModel, Field
from .enums import AggregationLevel


# --- Upload ---

class UploadInitRequest(BaseModel):
    filename: str
    file_size: int
    chunk_size: int = 2 * 1024 * 1024
    file_type: str = "csv"  # "csv" or "parquet"

class UploadInitResponse(BaseModel):
    session_id: str
    upload_id: str
    total_chunks: int

class UploadStatusResponse(BaseModel):
    upload_id: str
    status: str  # "uploading", "parsing", "ready", "error"
    chunks_received: int
    total_chunks: int
    parsing_progress: float = 0.0
    error: str | None = None


# --- Dataset ---

class ColumnInfo(BaseModel):
    name: str
    dtype: str
    null_count: int
    null_pct: float
    sample_values: list[str | float | int | None]

class KPIDefinition(BaseModel):
    name: str
    formula: str
    description: str = ""

class KPIValidateRequest(BaseModel):
    formula: str

class DatasetMetadata(BaseModel):
    session_id: str
    filename: str
    row_count: int
    time_range: tuple[str, str]
    timestamp_column: str
    dimension_columns: list[ColumnInfo]
    metric_columns: list[ColumnInfo]
    skipped_header_lines: int
    kpi_definitions: list[KPIDefinition] = Field(default_factory=list)

class DimensionValuesResponse(BaseModel):
    column: str
    values: list[str]
    count: int


# --- Model Registry ---

class ModelParam(BaseModel):
    name: str
    label: str
    type: str  # "int", "float", "bool", "select"
    default: float | int | bool | str
    min: float | int | None = None
    max: float | int | None = None
    step: float | int | None = None
    options: list[str] | None = None
    description: str = ""

class ModelInfo(BaseModel):
    id: str
    name: str
    description: str
    category: str  # "scorer" or "forecast"
    supports_multivariate: bool
    min_data_points: int
    requires_seasonality: bool = False
    requires_dimensions: bool = False
    gpu_accelerated: bool = False
    foundation: bool = False
    params: list[ModelParam]

class ModelCompatibility(BaseModel):
    model_id: str
    compatible: bool
    reason: str | None = None

class CompatibilityRequest(BaseModel):
    metrics: list[str]
    dimensions: list[str] | None = None
    dimension_filters: dict[str, list[str]] | None = None
    aggregation: AggregationLevel = AggregationLevel.HOURLY

class CompatibilityResponse(BaseModel):
    models: list[ModelCompatibility]


# --- Analysis ---

class DartsDetectionConfig(BaseModel):
    model_id: str
    metrics: list[str]
    dimensions: list[str] | None = None
    dimension_filters: dict[str, list[str]] | None = None
    aggregation: AggregationLevel = AggregationLevel.HOURLY
    params: dict[str, float | int | bool | str] = Field(default_factory=dict)
    detector_type: str = "quantile"
    detector_threshold: float = 0.95
    smoothing_window: int = 1  # 1 = no smoothing; >1 = rolling mean over N points
    transforms: list[str] = Field(default_factory=list)  # e.g. ["log", "diff", "scale_standard"]
    infill: str = "none"  # "none", "linear", "time", "ffill", "zero"
    scorer_id: str = "difference"  # "difference", "norm", "kmeans", "wasserstein"
    random_seed: int | None = None  # optional seed for reproducibility
    # Anomaly filtering
    persistence_damping: float = 0.0  # 0=off, 0.5=moderate, 1.0=strong
    min_anomaly_points: int = 1  # min points per region (1=keep all)
    volume_gate_metric: str | None = None  # reference metric column name
    volume_gate_threshold: float = 0.0  # suppress when reference < this

class DartsAnomalyPoint(BaseModel):
    timestamp: str
    metric: str
    value: float
    score: float
    is_anomaly: bool
    severity: str  # "low", "medium", "high"
    dimension_values: dict[str, str] | None = None

class ForecastPoint(BaseModel):
    timestamp: str
    metric: str
    predicted: float
    actual: float
    dimension_values: dict[str, str] | None = None

class AnomalyRegion(BaseModel):
    start: str
    end: str
    metric: str
    severity: str
    avg_score: float
    point_count: int
    dimension_values: dict[str, str] | None = None

class AnomalySummary(BaseModel):
    total_points_analyzed: int
    total_anomalies: int
    total_regions: int
    by_severity: dict[str, int]
    by_metric: dict[str, int]

class DartsAnomalyResult(BaseModel):
    run_id: str
    config: DartsDetectionConfig
    anomalies: list[DartsAnomalyPoint]
    scores: list[dict]
    forecast: list[ForecastPoint] | None = None
    summary: AnomalySummary
    regions: list[AnomalyRegion]


# --- Visualization ---

class TimeSeriesRequest(BaseModel):
    metrics: list[str]
    dimensions: list[str] | None = None
    dimension_filters: dict[str, list[str]] | None = None
    aggregation: AggregationLevel = AggregationLevel.HOURLY
    time_start: str | None = None
    time_end: str | None = None
    max_points: int = 3000
    smoothing_window: int = 1
    transforms: list[str] = Field(default_factory=list)
    infill: str = "none"

class SeriesData(BaseModel):
    name: str
    timestamps: list[str]
    values: list[float | None]

class TimeSeriesResponse(BaseModel):
    series: list[SeriesData]
    original_series: list[SeriesData] | None = None  # pre-transform data for overlay
    total_raw_points: int
    downsampled: bool

class ExportCsvRequest(BaseModel):
    metrics: list[str]
    dimensions: list[str] | None = None
    dimension_filters: dict[str, list[str]] | None = None
    time_start: str | None = None
    time_end: str | None = None
