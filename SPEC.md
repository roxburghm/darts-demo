# Anomaly Detection Playground — Definitive Build Specification

> **Purpose**: A single, complete specification document for rebuilding this application from scratch. Pass this file to a code-generation agent (Kiro AI / Claude / etc.) and the resulting application must reproduce the exact same UI, API, and behavior described below.

---

## 1. Product Overview

A self-service web app for time-series anomaly detection. A user uploads a CSV or Parquet file, the app classifies columns automatically, the user selects metrics/dimensions/aggregation, picks one of ~60 detection models, tunes its parameters, runs detection, and views anomaly scores overlaid on time-series charts with the ability to tune a threshold slider in real time and export results.

### 1.1 User-facing workflow (5 sequential steps)

| # | Page (route) | Purpose |
|---|---|---|
| 1 | **Upload** (`/upload`) | Drag-and-drop CSV or Parquet (≤ 500 MB). Chunked upload, real-time parsing progress. |
| 2 | **Preview** (`/preview/:sessionId`) | Inspect columns (dtype, null %, sample values) and 100 sample rows. |
| 3 | **Configure** (`/configure/:sessionId`) | Choose metrics, dimensions, dimension filters, aggregation level, define custom KPIs, live preview chart with transform controls. |
| 4 | **Models** (`/models/:sessionId`) | Browse models in 6 categories, search/filter (GPU/Foundation/Compatible), select & double-click to advance. |
| 5 | **Analysis** (`/analysis/:sessionId`) | Run detection, view scores + anomaly markers, drag a threshold slider for live recompute, expand regions for explanations, export CSV. |

The header is a **breadcrumb** (clickable backwards), with a **Clear** button (deletes session + resets) and a **theme toggle** (dark/light).

### 1.2 Privacy stance

Data is server-side cached for the session only. Never persisted permanently or shared. Auto-cleanup runs every 30 min; sessions expire after `DAD_SESSION_TTL_HOURS` (default 24). The Clear button instantly deletes all uploads/parsed/results.

---

## 2. Tech Stack

### Backend
- **Python ≥ 3.11**, **FastAPI ≥ 0.115**, **uvicorn[standard] ≥ 0.32**
- **Pydantic v2** + **pydantic-settings** (env-driven config with `DAD_` prefix)
- **pandas ≥ 2.2**, **polars ≥ 1.0**, **pyarrow ≥ 18**, **numpy ≥ 1.26**
- **darts ≥ 0.41** (time series), **pyod ≥ 2.0** (anomaly), **statsforecast ≥ 2.0**, **ruptures ≥ 1.1**, **prophet ≥ 1.1**, **xgboost ≥ 2.0**, **lightgbm ≥ 4.0**
- **apscheduler ≥ 3.10** (background cleanup), **websockets ≥ 13.0**, **aiofiles ≥ 24**, **python-multipart ≥ 0.0.18**
- Optional `[torch]` extras: torch, pytorch-lightning, huggingface-hub, safetensors, granite-tsfm
- Optional `[peer]` extras: dtaidistance ≥ 2.3, stumpy ≥ 1.12
- Soft installs (manual, conflicting deps): `momentfm --no-deps`, `lag-llama --no-deps`

### Frontend
- **Vue 3.5** with **TypeScript 5.6**, **Vite 6**, **vue-tsc 2.2**
- **vue-router 4.5** (hash-style, history mode)
- **Pinia 2.3** (state)
- **echarts 5.5** + **vue-echarts 7** (charts)
- **axios 1.7** (HTTP)
- ESLint optional

### Container
- Multi-stage Docker: Node 22 alpine → Python 3.12 slim. FastAPI serves built static files in production at `/app/static` (mounted under `/`).
- `docker-compose.yml`: single service `app`, port `8090:8000`, `app_data` volume for `/app/data`, env `DAD_SESSION_TTL_HOURS=48`, `DAD_MAX_UPLOAD_SIZE_MB=500`, `HF_HUB_CACHE=/app/data/hf_cache`. Healthcheck via `urllib.request.urlopen('http://localhost:8000/api/health')`.

### Native dev script (`./dev.sh`)
Kills processes on ports 8001/5173, then:
- backend: `uvicorn app.main:app --reload --port 8001` (from `backend/.venv`)
- frontend: `npm run dev` (port 5173)

---

## 3. Repository Layout

```
darts-demo/
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml
├── dev.sh                    # Dev launcher (ports 8001 + 5173)
├── README.md
├── MODELS.md
├── SPEC.md                   # this file
├── backend/
│   ├── pyproject.toml
│   ├── tests/
│   └── app/
│       ├── __init__.py
│       ├── main.py           # FastAPI factory + routers + SPA fallback
│       ├── config.py         # pydantic-settings (DAD_ prefix)
│       ├── api/
│       │   ├── upload.py
│       │   ├── datasets.py
│       │   ├── models.py
│       │   ├── visualization.py
│       │   └── ws.py
│       ├── models/
│       │   ├── enums.py
│       │   └── schemas.py
│       ├── services/
│       │   ├── session_manager.py
│       │   ├── csv_parser.py
│       │   ├── column_classifier.py
│       │   ├── dimension_parser.py
│       │   ├── aggregator.py
│       │   ├── kpi_computer.py
│       │   ├── downsampler.py
│       │   └── darts/
│       │       ├── registry.py
│       │       ├── compatibility.py
│       │       └── runner.py
│       ├── storage/
│       │   ├── parquet_store.py
│       │   └── result_cache.py
│       └── utils/
│           ├── cleanup.py
│           └── progress.py
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.ts
        ├── App.vue
        ├── router/index.ts
        ├── api/
        │   ├── client.ts
        │   ├── types.ts
        │   ├── upload.ts
        │   ├── datasets.ts
        │   ├── models.ts
        │   └── analysis.ts
        ├── stores/
        │   ├── upload.ts
        │   ├── dataset.ts
        │   ├── models.ts
        │   └── analysis.ts
        ├── views/
        │   ├── UploadView.vue
        │   ├── PreviewView.vue
        │   ├── ConfigureView.vue
        │   ├── ModelSelectView.vue
        │   └── AnalysisView.vue
        ├── components/
        │   ├── upload/
        │   │   ├── FileDropZone.vue
        │   │   └── UploadProgress.vue
        │   ├── dataset/
        │   │   ├── ColumnSelector.vue
        │   │   ├── DataPreview.vue
        │   │   ├── DimensionFilter.vue
        │   │   ├── AggregationControl.vue
        │   │   └── KPIEditor.vue
        │   ├── layout/
        │   │   └── AppHeader.vue
        │   ├── models/
        │   │   └── ModelCard.vue
        │   └── analysis/
        │       ├── ResultsChart.vue
        │       ├── ParamPanel.vue
        │       ├── AnomalyTable.vue
        │       └── AnalysisProgress.vue
        ├── composables/useWebSocket.ts
        ├── utils/
        │   ├── color.ts
        │   ├── constants.ts
        │   ├── formatters.ts
        │   └── explainer.ts
        └── styles/
            ├── variables.css
            ├── base.css
            └── transitions.css
```

---

## 4. Backend Configuration

### 4.1 `app/config.py`

```python
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Darts Anomaly Demo"
    data_dir: Path = Path(__file__).parent.parent / "data"
    upload_dir: Path = data_dir / "uploads"
    parsed_dir: Path = data_dir / "parsed"
    results_dir: Path = data_dir / "results"

    max_upload_size_mb: int = 500
    chunk_size_bytes: int = 2 * 1024 * 1024  # 2 MB
    session_ttl_hours: int = 24
    max_chart_points: int = 3000

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_prefix = "DAD_"   # e.g. DAD_SESSION_TTL_HOURS=48
```

On import, all three runtime directories are created. Override via env: `DAD_SESSION_TTL_HOURS`, `DAD_MAX_UPLOAD_SIZE_MB`, `DAD_MAX_CHART_POINTS`.

### 4.2 `app/main.py`

- FastAPI app with `lifespan` context that creates dirs and starts an `apscheduler.BackgroundScheduler` running `cleanup_expired_sessions` every 30 minutes.
- CORS middleware with `allow_origins=settings.cors_origins`, all methods/headers/credentials allowed.
- Routers mounted at `/api`:
  - `upload_router` → `/api/upload/*`
  - `datasets_router` → `/api/datasets/*`
  - `models_router` → `/api/models/*`
  - `viz_router` → `/api/viz/*`
  - `ws_router` → `/api/ws/*`
- `GET /api/health` → `{"status": "ok", "app": settings.app_name}`
- **SPA fallback**: if `/app/static/index.html` exists, mount `/assets`, then `GET /{full_path:path}` returns the file or `index.html` (and shortcuts on `api/` paths to a `{"detail": "Not found"}` 200, harmless because real API routes are matched first).

### 4.3 Filesystem layout (per session)

```
data/
├── uploads/<session_id>/
│   ├── chunks/chunk_000000 ... chunk_NNNNNN     (during upload)
│   ├── raw_upload.csv|parquet                   (after reassembly)
│   └── metadata.json
├── parsed/<session_id>/
│   ├── data.parquet                             (snappy compressed)
│   └── metadata.json                            (mirror, kept in sync)
└── results/<session_id>/
    └── <run_id>.json                            (one file per detection run)
```

`session_id` and `upload_id` are 12-char hex (`uuid.uuid4().hex[:12]`).

### 4.4 Session metadata schema

```json
{
  "session_id": "abc123...",
  "upload_id": "def456...",
  "filename": "telemetry.csv",
  "file_size": 12345678,
  "file_type": "csv",            // "csv" or "parquet"
  "total_chunks": 6,
  "chunks_received": 6,
  "status": "uploading|parsing|ready|error",
  "created_at": "2026-04-29T12:34:56+00:00",
  "parsing_progress": 100.0,
  "error": null,
  "dataset": {                    // populated when status=="ready"
    "session_id": "...",
    "filename": "telemetry.csv",
    "row_count": 139000,
    "time_range": ["2026-01-01T00:00:00", "2026-04-30T23:00:00"],
    "timestamp_column": "TimeStamp",
    "dimension_columns": [{name, dtype, null_count, null_pct, sample_values}],
    "metric_columns":    [{name, dtype, null_count, null_pct, sample_values}],
    "skipped_header_lines": 0,
    "kpi_definitions": [{name, formula, description}]
  }
}
```

`metadata.json` is kept identical in `uploads/<id>/` and `parsed/<id>/` (whichever exists is read; both are written when their dir exists).

---

## 5. Pydantic Schemas (canonical)

### 5.1 Enums (`app/models/enums.py`)

```python
class AggregationLevel(str, Enum):
    RAW = "raw"
    FIFTEEN_MIN = "15min"
    THIRTY_MIN  = "30min"
    HOURLY      = "1h"
    FOUR_HOUR   = "4h"
    DAILY       = "1d"

class DetectorType(str, Enum):
    QUANTILE  = "quantile"
    THRESHOLD = "threshold"
    IQR       = "iqr"

class DartsModelId(str, Enum):
    # All ~60 model IDs — see registry section below for the full list.
```

### 5.2 Schemas (`app/models/schemas.py`)

Upload:

```python
UploadInitRequest(filename: str, file_size: int, chunk_size=2*1024*1024, file_type="csv")
UploadInitResponse(session_id: str, upload_id: str, total_chunks: int)
UploadStatusResponse(upload_id, status, chunks_received, total_chunks,
                     parsing_progress=0.0, error=None)
```

Dataset:

```python
ColumnInfo(name: str, dtype: str, null_count: int, null_pct: float,
           sample_values: list[str|float|int|None])

KPIDefinition(name: str, formula: str, description: str = "")
KPIValidateRequest(formula: str)

DatasetMetadata(
    session_id, filename, row_count, time_range: tuple[str, str],
    timestamp_column, dimension_columns: list[ColumnInfo],
    metric_columns: list[ColumnInfo], skipped_header_lines: int,
    kpi_definitions: list[KPIDefinition] = [])

DimensionValuesResponse(column: str, values: list[str], count: int)
```

Models registry:

```python
ModelParam(
    name: str, label: str, type: "int|float|bool|select",
    default: float|int|bool|str, min: float|int|None=None,
    max: float|int|None=None, step: float|int|None=None,
    options: list[str]|None=None, description: str = "")

ModelInfo(
    id: str, name: str, description: str,
    category: "scorer|forecast",
    supports_multivariate: bool, min_data_points: int,
    requires_seasonality: bool = False,
    requires_dimensions: bool = False,
    gpu_accelerated: bool = False,
    foundation: bool = False,
    params: list[ModelParam])

ModelCompatibility(model_id: str, compatible: bool, reason: str|None=None)
CompatibilityRequest(metrics: list[str], dimensions=None,
                     dimension_filters=None, aggregation=AggregationLevel.HOURLY)
CompatibilityResponse(models: list[ModelCompatibility])
```

Analysis:

```python
DartsDetectionConfig(
    model_id: str,
    metrics: list[str],
    dimensions: list[str] | None = None,
    dimension_filters: dict[str, list[str]] | None = None,
    aggregation: AggregationLevel = AggregationLevel.HOURLY,
    params: dict = {},
    detector_type: str = "quantile",       # quantile|threshold|iqr
    detector_threshold: float = 0.95,
    smoothing_window: int = 1,             # 1 = no smoothing
    transforms: list[str] = [],            # log|diff|scale_standard|scale_minmax|boxcox|winsorize
    infill: str = "none",                  # none|linear|time|ffill|zero
    scorer_id: str = "difference",         # difference|norm|kmeans|wasserstein
    random_seed: int | None = None,
    persistence_damping: float = 0.0,      # 0..1
    min_anomaly_points: int = 1,
    volume_gate_metric: str | None = None,
    volume_gate_threshold: float = 0.0)

DartsAnomalyPoint(timestamp, metric, value, score, is_anomaly,
                  severity: "low|medium|high",
                  dimension_values: dict|None)

ForecastPoint(timestamp, metric, predicted, actual, dimension_values)

AnomalyRegion(start, end, metric, severity, avg_score, point_count, dimension_values)

AnomalySummary(total_points_analyzed, total_anomalies, total_regions,
               by_severity: dict[str, int], by_metric: dict[str, int])

DartsAnomalyResult(run_id, config: DartsDetectionConfig,
                   anomalies: list[DartsAnomalyPoint],
                   scores: list[dict],          # raw score timeseries
                   forecast: list[ForecastPoint] | None,
                   summary: AnomalySummary,
                   regions: list[AnomalyRegion])
```

Visualization:

```python
TimeSeriesRequest(metrics, dimensions=None, dimension_filters=None,
                  aggregation=HOURLY, time_start=None, time_end=None,
                  max_points=3000, smoothing_window=1, transforms=[], infill="none")

SeriesData(name: str, timestamps: list[str], values: list[float|None])

TimeSeriesResponse(series: list[SeriesData],
                   original_series: list[SeriesData] | None,   # pre-transform overlay
                   total_raw_points: int,
                   downsampled: bool)

ExportCsvRequest(metrics, dimensions=None, dimension_filters=None,
                 time_start=None, time_end=None)
```

---

## 6. REST API (mounted under `/api`)

### 6.1 Health
- **GET `/api/health`** → `{"status": "ok", "app": "Darts Anomaly Demo"}`

### 6.2 Upload
- **POST `/api/upload/init`** body=UploadInitRequest → UploadInitResponse. Rejects 400 if `file_size > max_upload_size_mb*1024*1024`. Computes `total_chunks = ceil(file_size / chunk_size)`. Creates session_id and upload_id (12-hex), creates `uploads/<sid>/`, writes initial metadata.
- **POST `/api/upload/{session_id}/chunk?chunk_index=<i>`** form file=binary. Rejects if session missing (404) or status≠"uploading" (400). Saves `chunks/chunk_{i:06d}`, increments `chunks_received`. Returns `{chunk_index, chunks_received}`.
- **POST `/api/upload/{session_id}/complete`** → 400 if not all chunks received; sets status=parsing, calls `session_manager.reassemble_chunks` (concatenates all chunks into `raw_upload.csv|parquet`, removes chunks dir), schedules background task `parse_csv_background` or `process_parquet_background` based on `file_type`. Returns `{session_id, status:"parsing"}`.
- **GET `/api/upload/{session_id}/status`** → UploadStatusResponse (polling fallback).

### 6.3 Datasets
- **DELETE `/api/datasets/{session_id}`** → `{status:"deleted", session_id}`. Recursively removes session in uploads/, parsed/, results/.
- **GET `/api/datasets/{session_id}`** → DatasetMetadata (400 if status≠ready).
- **GET `/api/datasets/{session_id}/preview?rows=100`** → `{columns: list[str], rows: list[dict], total_rows: int}` (NaN/Inf sanitized to null, pd.Timestamp → ISO).
- **GET `/api/datasets/{session_id}/download`** → file response of `data.parquet` named `<original-stem>.parquet`. If KPI defs exist, embeds them under Parquet schema metadata key `kpi_definitions` (JSON-encoded UTF-8) without modifying the stored file (uses temp file).
- **GET `/api/datasets/{session_id}/dimension-values`** → `[{column, values: sorted_unique[], count}]` per dimension column.
- **PUT `/api/datasets/{session_id}/kpis`** body=`list[KPIDefinition]`. Validates each formula on a 100-row sample of the parquet; on any failure returns 400 with `{message, errors:{name:err}}`. On success persists `kpi_definitions` into dataset metadata. Returns `{status:"ok", kpi_count}`.
- **POST `/api/datasets/{session_id}/kpis/validate`** body=`{formula}` → `{valid: bool, error?: str}`.

### 6.4 Models
- **GET `/api/models/`** → `list[ModelInfo]` (full registry).
- **POST `/api/models/{session_id}/compatibility`** body=CompatibilityRequest → CompatibilityResponse. Reads only the columns needed (excluding KPI names). Applies dimension_filters. Aggregates **without** dimensions to count effective per-series points. Counts unique groups of `dimensions[0]` for peer-model checks.
- **POST `/api/models/{session_id}/detect`** body=DartsDetectionConfig → `{run_id, status:"running"}`. Schedules background task that:
  1. Sends WS progress 10%/20%/40%.
  2. Reads parquet (only required cols) via thread executor.
  3. Applies dimension filters.
  4. Aggregates by ts_col + (dimensions or none); ensures KPI source columns are kept.
  5. Computes KPIs after aggregation.
  6. Calls `run_darts_detection(df, ts_col, config, progress_cb)` in executor.
  7. Sets `result.run_id = run_id` and saves to result cache.
  8. WS sends complete with `{run_id}`.
- **GET `/api/models/{session_id}/results/{run_id}`** → DartsAnomalyResult (404 if missing).

### 6.5 Visualization
- **POST `/api/viz/{session_id}/timeseries`** body=TimeSeriesRequest → TimeSeriesResponse.
  Pipeline:
  1. Read only required parquet columns (resolves KPI source cols).
  2. `df.reset_index(drop=True)`; coerce ts_col to datetime; drop NaT.
  3. Apply `dimension_filters` and time_start/time_end (tz-naive comparison).
  4. Aggregate via `aggregator.aggregate_data` with dimensions if provided.
  5. Compute KPIs after aggregation.
  6. Apply infill (if !=none) → smoothing (rolling mean, center=True) → transforms.
  7. If transforms exist, capture pre-transform copy as `original_series`.
  8. Group by dimensions and build `SeriesData` per metric. LTTB downsample if `len > max_points`. Sanitize NaN/Inf to null.
- **POST `/api/viz/{session_id}/export-csv`** body=ExportCsvRequest → CSV streaming response (`raw-export.csv`). Same pipeline minus transforms/smoothing/infill: outputs ts_col + dimensions + metrics in long form.

### 6.6 WebSocket
- **`/api/ws/{session_id}`**: client receives JSON strings:
  - `{"type":"progress", "stage":"parsing|analysis", "progress":<0-100>, "detail":"..."}`
  - `{"type":"complete", "stage":"parsing|analysis", ...payload}` (analysis includes `{run_id}`)
  - `{"type":"error", "detail":"..."}`
  - `{"type":"ping"}` keepalive every 30 s when no message.

---

## 7. Backend Services

### 7.1 `session_manager.py`
- `create_session(filename, file_size, total_chunks, file_type)`: creates dir + metadata.json.
- `get_metadata(sid)`: tries `uploads/<sid>/metadata.json` then `parsed/<sid>/metadata.json`.
- `update_metadata(sid, updates)`: read-modify-write to whichever metadata files exist.
- `reassemble_chunks(sid)`: writes `raw_upload.csv` and removes `chunks/`.
- `cleanup_session(sid)`: rmtree session dirs in all three bases.

### 7.2 `csv_parser.py`

**Header detection** (`detect_header_row`): scans first 15 lines, picks the first line that:
- has ≥ 80 % of the max field count,
- has all non-empty fields,
- does **not** contain values matching `^\d{4}[-/]\d{2}[-/]\d{2}`, `^--$`, `^\d+\.\d+$`, or `^\d{10,}$`,
- has ≥ 50 % alphabetic-prefixed fields.

Falls back to row 0.

**`parse_csv(file_path)`**: `polars.read_csv(skip_rows=detected, null_values=["--","","NA","N/A","null","NULL"], try_parse_dates=True, infer_schema_length=10000, ignore_errors=True)`. Trims whitespace/quotes from column names.

**`parse_csv_background(sid, file_path)`** (async): emits WS progress 5/40/60/85%, runs parse in executor, classifies columns, expands structured dimensions, deduplicates by `(ts_col, *dim_cols)` keeping last, writes parquet, builds dataset metadata, sets status=ready, deletes original CSV, sends complete.

**`process_parquet_background(sid, file_path)`** (async, similar): reads with pyarrow, extracts embedded `kpi_definitions` from schema metadata if present, casts string `object` columns to `category` (≈ 80 % memory savings), classifies, dedupes, writes parquet.

### 7.3 `column_classifier.py`

Constants:
- `KNOWN_TIMESTAMP_NAMES = {timestamp, time, datetime, date_time, start_time, starttime, start, end_time, endtime, period_start, period_end, collection_time, collectiontime, date}`
- `KNOWN_DIMENSION_NAMES = {node_name, nodename, node, ne_version, neversion, network, network_type, network_name, networkname, moid, mo_id, mme_function, mmefunction, site, site_name, sitename, cell, cell_name, cellname, region, area, vendor, technology, tech, customer_type, customertype, cust_type, subscriber_type, service_type, servicetype, interface, link}`
- `KNOWN_IGNORE_NAMES = {counter_group, countergroup, period_duration, periodduration, reliability_indicator, reliabilityindicator, granularity_period, granularityperiod, object_type, objecttype}` (dropped, not classified)

`classify_columns(df) -> {timestamp_column, dimension_columns, metric_columns}`:
1. Detect timestamp by name → datetime dtype → string column whose ≥80 % of first 20 non-null values parse via `pd.to_datetime`.
2. Skip ignore-list columns.
3. Dimension if name in known list, OR string dtype with `nunique < max(rows*0.01, 100)`.
4. Metric if numeric dtype.
5. Else: dimension if string-like, else discard.

Each ColumnInfo carries `null_count`, `null_pct` (4-dp), and 5 sample values (numpy types coerced to native Python).

### 7.4 `dimension_parser.py` — `expand_structured_dimensions`

When a dimension column is in `{node_name, nodename, node}` and ≥80 % of its non-null values match `^[A-Za-z0-9]{11}$`, generate four new dimension columns:
- `NODE_DEVICE_TYPE` = chars [0:3]
- `NODE_POOL` = chars [3:5]
- `NODE_LOCATION` = chars [5:8]
- `NODE_CUSTOMER_TYPE` = chars [8:11]

Values uppercased. Rows that don't match get NaN in new columns.

### 7.5 `aggregator.py`

```python
AGG_RULES = {"15min":"15min", "30min":"30min", "1h":"1h", "4h":"4h", "1d":"1D"}
```

`aggregate_data(df, ts_col, metric_cols, aggregation, dimension_cols=None)`:
- Always `sum` aggregation.
- For RAW: `collapse_by_timestamp` — group by `[ts_col, *dim_cols]` and sum.
- For others: set ts_col as index, then either `groupby(dim_cols).resample(rule).agg(sum)` or just `.resample(rule).agg(sum)`. Reset index back to flat columns.

### 7.6 `kpi_computer.py`

KPIs are formulas that can reference any dataset column (including hidden source columns). Supported tokens:
- arithmetic: `+ - * / ** // %`
- comparison: `> < >= <= == !=`
- logic: `& | ~`
- functions: `abs sqrt log log10 exp sin cos tan`

NOT supported: `max() min() if/else`, arbitrary Python.

Implementation: `_normalize_formula` collapses whitespace, `_backtick_formula` wraps any column name found in the formula in backticks (longest first to avoid partial overwrites). Calls `df.eval(...)` with the normalized & backticked formula.

`validate_kpi(df, formula)`: evaluates against a 100-row sample, returns None or a friendly error.

Friendly error parser (`_friendly_formula_error`):
- `"has no attribute 'type'"` or `UndefinedVariableError` → list unknown variables.
- `"is not defined"` → name extraction.
- Else: append `(possible unrecognised variable(s): ...)`.

`get_kpi_source_columns(kpi_definitions, available_columns)`: returns columns whose name appears literally anywhere in any formula string (used to load source cols when only the KPI is selected).

### 7.7 `downsampler.py` — LTTB

`lttb_downsample(timestamps, values, target_points)` — Largest Triangle Three Buckets algorithm. Always keeps first/last points; for each intermediate bucket, picks the point that forms the largest triangle with the previously selected point and the next bucket's average. Forward-fills `None` values internally so areas stay computable.

`lttb_downsample_band(timestamps, lower, upper, target_points)`: runs LTTB on the midpoint and re-uses the chosen indices for both bands.

### 7.8 `storage/parquet_store.py`

```python
class ParquetStore:
    def write(self, sid, df) -> None       # snappy compression
    def read(self, sid, columns=None, limit=None) -> pd.DataFrame
    def exists(self, sid) -> bool
```

`read` filters requested columns against schema, logs warnings for unavailable columns, raises `FileNotFoundError` if none remain.

### 7.9 `storage/result_cache.py`

```python
class ResultCache:
    def save(self, sid, run_id, result: DartsAnomalyResult)  # JSON, indent=2
    def load(self, sid, run_id) -> DartsAnomalyResult | None
    def exists(self, sid, run_id) -> bool
```

### 7.10 `utils/cleanup.py` — `cleanup_expired_sessions()`
For each base dir (uploads, parsed, results), iterate session subdirs:
1. Try `metadata.json["created_at"]` ISO string.
2. Fallback to mtime of metadata.json on JSON decode error.
3. Fallback to dir mtime if no metadata.

Compare with UTC now and delete via `shutil.rmtree(..., ignore_errors=True)` if older than `settings.session_ttl_hours`.

### 7.11 `utils/progress.py` — `ProgressBroadcaster`

Singleton `progress_broadcaster`. Per-session list of `asyncio.Queue`s; `subscribe()` registers, `unsubscribe()` removes (cleans up empty session entries). Methods:
- `await broadcast(sid, type, data)` — fire-and-forget put on every queue.
- `await send_progress(sid, stage, progress, detail="")` — rounds progress to 1 decimal, type=`"progress"`.
- `await send_error(sid, error)`
- `await send_complete(sid, stage, data=None)` — type=`"complete"`, stage included.

### 7.12 WebSocket router
On connect, subscribe a queue; loop `await asyncio.wait_for(queue.get(), timeout=30.0)` and forward as text. On timeout, send `{"type":"ping"}`. On disconnect, unsubscribe.

---

## 8. Model Registry (`services/darts/registry.py`)

Returns `list[ModelInfo]` from `get_all_models()`. The frontend uses this to render forms and parameter ranges.

Categorization (used in frontend grouping):
- **Standalone Scorers**: PyOD/Darts native (kmeans, isolation_forest, lof, ecod, wasserstein, copod, hbos, knn, ocsvm, inne, loda, cblof, rod, abod, sos, lscp, sod, vae, pca, mcd) + statistical (modified_zscore, stl_gesd, spectral_residual, cusum, hampel, changepoint) + deep (deep_svdd, autoencoder, dagmm, anomaly_transformer, tranad).
- **Peer/Cohort** (`requires_dimensions=True`): peer_divergence, peer_pca, peer_functional_depth, peer_feature_isolation, peer_dtw_lof, peer_matrix_profile.
- **Forecast — Local**: exponential_smoothing, fft, theta, arima, auto_arima, four_theta, naive_mean, naive_seasonal, naive_drift, naive_moving_avg, croston, prophet.
- **Forecast — Regression/ML**: linear_regression, random_forest, lightgbm, xgboost.
- **Forecast — Deep Learning**: nbeats, nhits, tft, dlinear, nlinear, tcn, transformer, block_rnn, tide, tsmixer.
- **Foundation**: chronos2, timesfm, tspulse, moment, lag_llama (`foundation=True`).

`gpu_accelerated=True` for the 21 GPU models: vae, deep_svdd, autoencoder, dagmm, anomaly_transformer, tranad, nbeats, nhits, tft, dlinear, nlinear, tcn, transformer, block_rnn, tide, tsmixer, chronos2, timesfm, tspulse, moment, lag_llama.

### 8.1 Full parameter table

For each model: `id`, `name`, `description`, `category` (scorer|forecast), `supports_multivariate`, `min_data_points`, `requires_dimensions`, `gpu_accelerated`, `foundation`, plus the params below. Param shape: `{name, label, type, default, min, max, step, options, description}`.

#### Density / distance scorers (category="scorer", multivariate=true)

| ID | min pts | Params (name = default in [min, max]) |
|---|---|---|
| `kmeans` | 50 | window=10 [3,100]; k=8 [2,50] |
| `isolation_forest` | 30 | window=10 [1,100]; n_estimators=100 [50,500]; contamination=0.1 [0.01,0.5] |
| `lof` | 30 | window=10 [1,100]; n_neighbors=20 [5,100]; contamination=0.1 |
| `ecod` | 30 | window=10; contamination=0.1 |
| `wasserstein` | 50 | window=10 [3,100] |
| `copod` | 30 | window=10; contamination=0.1 |
| `hbos` | 30 | window=10; n_bins=10 [5,100]; contamination=0.1 |
| `knn` | 30 | window=10; n_neighbors=20 [5,100]; contamination=0.1 |
| `ocsvm` | 30 | window=10; kernel=select(rbf,linear,poly,sigmoid)=rbf; contamination=0.1 → mapped to ν |
| `inne` | 30 | window=10; n_estimators=200 [50,500]; contamination=0.1 |
| `loda` | 30 | window=10; n_bins=10 [5,50]; n_random_cuts=100 [10,500]; contamination=0.1 |
| `cblof` | 30 | window=10; n_clusters=8 [2,20]; alpha=0.9 [0.5,1.0]; contamination=0.1 |
| `rod` | 30 | window=10; contamination=0.1 |
| `abod` | 30 | window=10; n_neighbors=10 [3,50]; method=select(fast,default)=fast; contamination=0.1 |
| `sos` | 30 | window=10; perplexity=4.5 [1.0,50.0]; contamination=0.1 |
| `lscp` | 30 | window=10; contamination=0.1 |
| `sod` | 30 | window=10; n_neighbors=20 [5,50]; ref_set=10 [2,30]; contamination=0.1 |
| `vae` (gpu) | 50 | window=20 [5,200]; epochs=30 [5,200]; hidden_neurons=select("32,16,16,32"|"64,32,32,64"|"128,64,32,64,128")="64,32,32,64"; latent_dim=2 [1,16]; contamination=0.1 |
| `pca` | 30 | window=10; n_components=5 [1,50]; contamination=0.1 |
| `mcd` | 30 | window=10; support_fraction=0.5 [0.1,1.0]; contamination=0.1 |

#### Statistical scorers

| ID | min pts | Params |
|---|---|---|
| `modified_zscore` | 10 | threshold=3.5 [1.0,10.0] |
| `stl_gesd` | 48 | period=24 [2,365]; max_anomaly_pct=0.10 [0.01,0.50] |
| `spectral_residual` | 30 | spectral_window=3 [1,21] (odd); score_window=21 [3,101] (odd) |
| `cusum` | 20 | drift=0.5 [0,5] (k in σ); threshold_h=5.0 [1,20] (h in σ) |
| `hampel` | 10 | window=11 [3,101] (odd); n_sigma=3.0 [1,10] |
| `changepoint` | 20 | model=select(rbf,l2,l1,normal)=rbf; penalty=3.0 [0.5,20.0] |

#### Deep neural scorers (gpu_accelerated)

| ID | min pts | Params |
|---|---|---|
| `deep_svdd` | 50 | window=20 [5,200]; epochs=30 [5,200]; contamination=0.05 |
| `autoencoder` | 50 | window=20; epochs=30; hidden_neurons=select(...)="64,32,32,64"; dropout_rate=0.2 [0,0.5]; contamination=0.05 |
| `dagmm` | 100 | window=20; epochs=30; hidden_dim=16 [4,64]; n_components=4 [2,16]; lr=0.001 [0.0001,0.01] |
| `anomaly_transformer` | 100 | window=20; epochs=30; d_model=64 [16,256]; n_heads=4 [1,8]; n_layers=2 [1,6]; lr=0.0001 [1e-5,0.01] |
| `tranad` | 100 | window=20; epochs=30; d_model=64; n_heads=4; n_layers=2; lr=0.0001 |

#### Peer / Cohort (requires_dimensions=True)

| ID | min pts | mv | Params |
|---|---|---|---|
| `peer_divergence` | 10 | yes | method=select(median,mean)=median; normalization=select(pct,mad,zscore)=pct; min_peers=3 [2,100] |
| `peer_pca` | 10 | yes | n_components=0.95 [0.5,0.999]; min_peers=3 |
| `peer_functional_depth` | 10 | no | min_peers=3 |
| `peer_feature_isolation` | 20 | no | contamination=0.1 [0.01,0.5]; min_peers=3 |
| `peer_dtw_lof` | 10 | no | dtw_window=10 [1,100]; lof_neighbors=3 [1,20]; min_peers=3 |
| `peer_matrix_profile` | 50 | no | subsequence_length=24 [4,200]; min_peers=3 |

#### Foundation (gpu, foundation=True)

| ID | min pts | mv | Params |
|---|---|---|---|
| `chronos2` | 100 | yes | input_chunk_length=64 [8,512]; hub_model_name=select(autogluon/chronos-2-small, amazon/chronos-2, autogluon/chronos-2-synth)=autogluon/chronos-2-small |
| `timesfm` | 100 | yes | input_chunk_length=64 |
| `tspulse` | 1536 | yes | scoring_mode=select(time+fft,time,fft)=time+fft; aggregation_length=64 [8,256]; smoothing_length=8 [1,64] |
| `moment` | 512 | yes | context_length=512 [64,512]; model_variant=select(AutonLab/MOMENT-1-small, base, large)=AutonLab/MOMENT-1-large |
| `lag_llama` | 100 | yes | context_length=32 [16,128]; prediction_length=1 [1,24]; num_samples=100 [20,500] |

#### Forecast — Local (category="forecast", multivariate=true)

| ID | min pts | Params |
|---|---|---|
| `exponential_smoothing` | 48 | seasonal_periods=24 [2,365] |
| `fft` | 100 | nr_freqs_to_keep=10 [1,100] |
| `theta` | 30 | theta=2.0 [0,10]; season_mode=select(multiplicative,additive,none)=multiplicative |
| `arima` | 30 | p=1 [0,10]; d=1 [0,3]; q=1 [0,10] |
| `auto_arima` | 30 | season_length=24 [1,365] |
| `four_theta` | 30 | theta=2.0; season_mode |
| `naive_mean` | 10 | (none) |
| `naive_seasonal` | 10 | K=24 [1,365] |
| `naive_drift` | 10 | (none) |
| `naive_moving_avg` | 10 | input_chunk_length=24 [2,200] |
| `croston` | 10 | version=select(classic,optimized,sba)=classic |
| `prophet` | 30 | growth=select(linear,logistic,flat)=linear; changepoint_prior_scale=0.05 [0.001,0.5]; seasonality_mode=select(additive,multiplicative)=additive; seasonality_prior_scale=10.0 [0.01,50]; daily_seasonality=auto; weekly_seasonality=auto; yearly_seasonality=auto |

#### Forecast — Global Regression/ML (multivariate=true)

| ID | min pts | Params |
|---|---|---|
| `linear_regression` | 30 | lags=24 [2,200] |
| `random_forest` | 30 | lags=24; n_estimators=100 [10,500]; max_depth=10 [2,50] |
| `lightgbm` | 30 | lags=24; n_estimators=100 [10,1000]; max_depth=6 [2,20]; learning_rate=0.1 [0.01,1.0] |
| `xgboost` | 30 | lags=24; n_estimators=100; max_depth=6; learning_rate=0.1 |

#### Forecast — Deep Learning (multivariate=true, gpu)

Shared params on all DL forecasters:
- `input_chunk_length=24 [4,200]`
- `n_epochs=10 [1,100]`
- `learning_rate=0.001 [1e-4,0.1]`
- `batch_size=32 [8,256]`
- `dropout=0.1 [0,0.5]`

Extras:

| ID | min pts | Extra params |
|---|---|---|
| `nbeats` | 50 | num_stacks=10 [2,30] |
| `nhits` | 50 | num_stacks=3 [2,10] |
| `tcn` | 30 | num_filters=3 [1,32] |
| `block_rnn` | 30 | rnn_model=select(LSTM,GRU)=LSTM; hidden_dim=25 [8,128] |
| `transformer` | 50 | d_model=16 [8,128]; nhead=4 [1,16] |
| `tft` | 50 | hidden_size=16 [8,128] |
| `tide` | 30 | hidden_size=16 |
| `dlinear` | 30 | (shared only) |
| `nlinear` | 30 | (shared only) |
| `tsmixer` | 30 | hidden_size=16 |

> Implementation note: all params live in registry.py; the frontend renders them generically by `type` and `options`.

### 8.2 Compatibility (`compatibility.py`)

`check_compatibility(num_metrics, num_data_points, num_dimensions, num_dimension_groups)` returns a `ModelCompatibility` per model:

```
if model.requires_dimensions and num_dimensions == 0:
    incompatible: "Requires at least one dimension selected (e.g. NODE_NAME)."
elif model.requires_dimensions and num_dimension_groups < 3:
    incompatible: f"Requires at least 3 peer groups. Your dimension selection has {num_dimension_groups} groups."
elif not model.supports_multivariate and num_metrics > 1:
    incompatible: f"Univariate only — supports 1 metric at a time. You have {num_metrics} metrics selected."
elif num_data_points < model.min_data_points:
    incompatible: f"Requires at least {model.min_data_points} data points. Your data has {num_data_points}."
else: compatible
```

---

## 9. Detection Pipeline (`services/darts/runner.py`)

### 9.1 Constants
- `GLOBAL_FORECAST_MODELS = {linear_regression, random_forest, lightgbm, xgboost, nbeats, nhits, tft, dlinear, nlinear, tcn, transformer, block_rnn, tide, tsmixer, chronos2, timesfm}`
- `FOUNDATION_MODELS = {chronos2, timesfm, tspulse, moment, lag_llama}`
- `FOUNDATION_CHUNK_SIZE = 128`
- `MAX_FOUNDATION_POINTS = 3000` (downsample longer foundation inputs).

### 9.2 Public functions
- `apply_infill(df, metric_cols, infill, ts_col)`: `linear`, `time` (datetime-index interpolation), `ffill`, `zero`, `none`.
- `apply_transforms(df, metric_cols, transforms)`: applied **in the order received**. Supported: `log` (log1p of `max(0,x)`), `boxcox` (positive only, falls back to `log`), `diff` (first-order, back-fill), `scale_standard`, `scale_minmax`, `winsorize` (clip to 1st/99th percentiles).
- `run_darts_detection(df, ts_col, config, progress_callback) -> DartsAnomalyResult`.

### 9.3 Pipeline
1. Apply infill → smoothing (centered rolling mean, `min_periods=1`) → transforms.
2. Dispatch by `model_id`:
   - `peer_*` → `_run_peer_<x>_pipeline` (require dimensions; min 3 groups).
   - `tspulse | stl_gesd | spectral_residual | cusum | hampel | changepoint | modified_zscore` → custom statistical pipeline.
   - `dagmm | anomaly_transformer | tranad | moment | lag_llama` → custom deep pipeline.
   - else if `category == "scorer"` → `_run_scorer_pipeline` (PyODScorer wrapper + VAE/PCA/MCD).
   - else if `model_id in GLOBAL_FORECAST_MODELS` → `_run_global_forecast_pipeline` (fit-once, historical forecasts; foundation models use stride=128).
   - else → `_run_forecast_pipeline` (sliding-window local forecaster, retrain ~20 times across the series).

### 9.4 Detector mapping
- `quantile`: `QuantileDetector(high_quantile=min(threshold, 0.999))`.
- `threshold`: `ThresholdDetector(high_threshold=threshold)`.
- `iqr`: `IQRDetector(scale=threshold)`.

### 9.5 Severity
```python
def _classify_severity(score, threshold):
    if score > threshold * 2.0: return "high"
    if score > threshold * 1.5: return "medium"
    return "low"
```
Threshold is `quantile(positive_scores, min(detector_threshold, 0.999))` of the produced scores.

### 9.6 Region merging
Group anomaly points by `(metric, dim_values_key)`, sort by timestamp, merge consecutive points with gap ≤ `2 × median_step`. Emit `AnomalyRegion(start, end, metric, severity=worst_in_region, avg_score, point_count, dimension_values)`.

### 9.7 Persistence damping
Filter regions to `point_count >= min_anomaly_points`. Then boost `effective_score = avg_score × (1 + damping × log2(point_count))` and reclassify severity. Drop anomaly points that are no longer in any surviving region.

### 9.8 Volume gate
If `volume_gate_metric` is set, build a `timestamp → volume_value` lookup and remove anomaly points where that value < `volume_gate_threshold`.

### 9.9 Statistical pipeline formulas

**Modified Z-Score**: `0.6745 × |x − median| / MAD`. Anomaly if score > `threshold` (default 3.5). Baseline=median.

**STL + GESD**: STL decomposition (period from param). Iterative GESD test on residuals up to `max_anomaly_pct × n` outliers; critical value `((n−i−1)·t_crit) / sqrt((n−i−2+t_crit²)·(n−i))` at α=0.05. Score = `|residual| / MAD(residuals)`. Baseline = trend + seasonal.

**Spectral Residual**: FFT → log_amplitude → `log_amp − moving_avg(log_amp, spectral_window)` → IFFT magnitude² → smoothed by `score_window`.

**CUSUM**: with `k = drift × σ`, `h = threshold_h × σ`, two-sided:
```
s_pos[j] = max(0, s_pos[j-1] + (x[j]-μ) - k)
s_neg[j] = max(0, s_neg[j-1] - (x[j]-μ) - k)
score[j] = max(s_pos[j], s_neg[j])
```
Anomaly if score > h. Baseline = μ.

**Hampel filter**: sliding window odd-length; `MAD`; `σ_est = 1.4826 × MAD`; score = `|x − median| / σ_est`. Anomaly if > `n_sigma`.

**Change point (PELT, ruptures)**: with `model` cost and `penalty × log(n)`. Within each segment baseline = mean; score = `|x − baseline| / global_std`; ±2 timesteps around CP boosted by jump magnitude.

### 9.10 Peer pipelines

All peer pipelines:
- Use `dimensions[0]` as peer column.
- Build `(N peers × T timestamps × M metrics)` array, interpolate per-peer gaps to common time index.
- Compute consensus and per-peer score per metric.
- Compute global per-metric threshold from all peers; only emit anomaly points at original (non-interpolated) timestamps.
- Baseline returned as peer median (forecast points).

**Peer Divergence**: deviation = `|x − consensus|`; normalize by `pct` (`× 100 / max(|consensus|, eps)`), `mad`, or `zscore`.

**Peer PCA Reconstruction**: per metric, build `N × T` matrix, standardize columns, PCA retaining `n_components` variance fraction; score = `|actual − reconstructed|`.

**Peer Functional Depth**: per timestamp envelope `IQR = q75-q25`; `envelope_score = |x − median| / IQR`. Modified Band Depth across peers; `final_score = envelope_score × (1 + 1.0 × (1 − MBD))`.

**Peer Feature Isolation**: 17-D feature vector per peer (mean, std, skew, kurtosis, median, IQR, range, diff_std, mean_abs_diff, autocorr lags 1/5/10, trend slope, zero-crossing rate, spectral entropy). IsolationForest scores → combined with envelope distance: `score = envelope_dist × (1 + node_weight × 2.0)`.

**Peer DTW + LOF**: pairwise DTW (with `dtw_window`, `use_pruning=True`); LOF on precomputed distance matrix; node_weight = `−LOF.negative_outlier_factor_`; combined like above.

**Peer Matrix Profile**: per node `MP = stumpy.stump(node, m=subsequence_length, T_B=consensus)`; node score over time = MP nearest-neighbor distance, padded/centered to T.

---

## 10. Frontend

### 10.1 Vite config (`vite.config.ts`)

```ts
{
  resolve: { alias: { '@': resolve(__dirname, 'src') } },
  server: {
    port: 5173,
    host: true,
    allowedHosts: ['anom.roxb.in'],
    proxy: {
      '/api': { target: 'http://localhost:8001', changeOrigin: true, ws: true }
    }
  }
}
```

### 10.2 Bootstrap

`main.ts`: createApp + Pinia + router; imports `styles/base.css` and `styles/transitions.css`; mounts `#app`.

`App.vue`:
```html
<div class="app">
  <AppHeader />
  <main class="app-main">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in"><component :is="Component" /></transition>
    </router-view>
  </main>
</div>
```

### 10.3 Router (`router/index.ts`)

History mode. Routes:
- `/` → redirect `/upload`
- `/upload` (name="upload") → UploadView
- `/preview/:sessionId` (name="preview", `props: true`) → PreviewView
- `/configure/:sessionId` (name="configure", props) → ConfigureView
- `/models/:sessionId` (name="models", props) → ModelSelectView
- `/analysis/:sessionId` (name="analysis", props) → AnalysisView

All views are lazy-loaded (`() => import('@/views/...')`).

### 10.4 API client (`api/client.ts`)

```ts
import axios from 'axios'
export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' }
})
```

Typed wrappers in `api/upload.ts`, `api/datasets.ts`, `api/models.ts`, `api/analysis.ts` mirror section 6 endpoints. All TS types live in `api/types.ts` and match the Pydantic shapes in section 5.

### 10.5 Pinia stores

#### `stores/upload.ts`
State: `sessionId, uploadId, filename, fileSize, chunksUploaded, totalChunks, parsingProgress, status: 'idle'|'uploading'|'parsing'|'ready'|'error', error`.
Computed: `uploadProgress = chunksUploaded / totalChunks * 100`.
Actions:
- `upload(file)`: detect file_type from extension; call `initUpload`; loop chunked upload (slice 2 MB); call `completeUpload`; status remains `'parsing'` until WS or polling sets `'ready'`.
- `setParsingProgress`, `setReady`, `setError`, `reset`.

#### `stores/dataset.ts`
State: `metadata, dimensionValues, selectedMetrics, selectedDimensions, dimensionFilters, aggregation: AggregationLevel, loading, kpiDefinitions`.
Actions: `loadMetadata`, `toggleMetric`, `toggleDimension` (also clears its filter), `setDimensionFilter`, `addKPI`, `removeKPI`, `saveKPIs`, `persistSelections`/`restoreSelections` (sessionStorage key `dataset-selections:{sessionId}`), `reset`.

#### `stores/models.ts`
State: `models, compatibility, selectedModelId, params, detectorType, detectorThreshold, smoothingWindow, transforms, infill, scorerId, showFitLine, persistenceDamping, minAnomalyPoints, volumeGateMetric, volumeGateThreshold, currentRunId, results, isRunning, progress, progressStage, error`.
Computed:
- `selectedModel`: model object.
- `thresholdScore`: numeric cutoff derived from `detectorType`/`detectorThreshold` against `results.scores` (quantile/threshold/iqr fence Q3 + threshold·IQR).
- `effectiveAnomalies`: filtered from raw scores using current `thresholdScore`.
- `effectiveRegions`: regions merged from `effectiveAnomalies` then filtered by `minAnomalyPoints`, severity boosted by `persistenceDamping × log2(point_count)`.
- `effectiveSummary`: `total_anomalies, by_severity, by_metric` from effective points.
- `regionExplanations`: map<key,string> via `explainRegion`.

Actions: `loadModels`, `loadCompatibility`, `selectModel` (resets `params` to model defaults), `isCompatible`, `getIncompatibilityReason`, `runDetection`, `loadResults`, `setProgress`, `setComplete`, `persistSelection`/`restoreSelection` (sessionStorage key `model-selection:{sessionId}`), `reset`.

#### `stores/analysis.ts`
State: `chartData: TimeSeriesResponse|null, error`.
Action: `loadChartData(sessionId, metrics, dimensions, dimensionFilters, aggregation, timeStart?, timeEnd?, smoothingWindow?, transforms?, infill?)`.

### 10.6 Composable: `useWebSocket(sessionId)`

Returns `{ connected, lastMessage, on(type, handler), disconnect() }`. URL `${ws|wss}://${host}/api/ws/{sessionId}`. Auto-reconnect with exponential backoff up to 16 s, max 5 retries (analysis) / unlimited (upload). Handler subscription supports `"*"` wildcard. Parses each text frame as JSON.

### 10.7 Views

#### UploadView
- Renders `<FileDropZone @file-selected="handleFile">` and `<UploadProgress :filename :fileSize :status :uploadProgress :parsingProgress :error @retry>`.
- Privacy banner.
- WebSocket subscribed once `sessionId` exists; listens for `progress` and `complete` of stage `parsing`. Polling fallback every 2 s on `getUploadStatus`.
- On `status==='ready'` → `router.push({name:'preview', params:{sessionId}})`.

#### PreviewView
- onMount: `loadMetadata` + `getPreview(rows=100)`.
- Cards: filename, row count, metric/dimension counts, time range.
- `<DataPreview :columns :rows :totalRows :nullPcts>` — fixed header table; null% color: red ≥100, orange >0, green 0.
- Button → ConfigureView.

#### ConfigureView
- Two-column: left controls / right live chart preview.
- `<AggregationControl>` button row; `<ColumnSelector title="Metrics">` and `<ColumnSelector title="Dimensions">` with search + Select-All/Clear; `<DimensionFilter>` (only when dimensions selected); `<KPIEditor>`.
- Right: `<ResultsChart :chartData>` of `analysisStore.chartData`.
- Debounce chart reload (500 ms) on selection changes.
- Footer: count summary, Back, "Select Model" (disabled if no metrics).
- On proceed: `dataset.persistSelections` then push to ModelSelectView.

#### ModelSelectView
- onMount: `models.loadModels()` then `models.loadCompatibility(sessionId)`.
- Header: search input, chips (GPU / Foundation / Compatible toggles), result count, view toggle (grid ↔ condensed list).
- Sections (each rendered if non-empty after filter):
  1. **Standalone Scorers** — `category=='scorer' && !requires_dimensions && !foundation`
  2. **Peer/Cohort Analysis** — `requires_dimensions==true`
  3. **Forecast-Based** — `category=='forecast'` excluding regression/ML and DL groups below
  4. **Regression / ML** — ids `linear_regression, random_forest, lightgbm, xgboost`
  5. **Deep Learning** — ids `nbeats, nhits, tft, dlinear, nlinear, tcn, transformer, block_rnn, tide, tsmixer`
  6. **Foundation Models** — `foundation==true`
- Each model rendered as `<ModelCard :model :compatible :reason :selected :condensed @select @proceed>`.
- Footer: selected model name + "Run Analysis" button (disabled if incompatible).
- Proceed: `models.persistSelection`, then push to AnalysisView.

#### AnalysisView
- Top toolbar: Back, model name, summary badges (total / high / med / low), Show Fit checkbox, Lock Zoom, Reset Zoom.
- Center: `<ResultsChart>` (flex-1, min 300 px).
- Bottom panel (height 200 px): either `<AnalysisProgress>` while running, `<AnomalyTable>` when results exist, error banner, or empty state.
- Right sidebar (300 px): `<ParamPanel>`.
- WebSocket: subscribe to `progress`, `complete` (`stage='analysis'`), `error`.
- On model.run: save current zoom range → call backend; on complete + loadResults → restore zoom if Lock Zoom.
- Threshold slider triggers no API call (recompute is client-side via `effectiveAnomalies`).
- Transforms / smoothing / infill changes reload chart data (debounced 300 ms).
- AnomalyTable double-click region → `chart.zoomToRange(start, end)`.

### 10.8 Components

**FileDropZone** — drag-drop zone, `accept=".csv,.parquet,.csb,.txt"`, emits `file-selected`.

**UploadProgress** — props `{filename, fileSize, status, uploadProgress, parsingProgress, error}`, emits `retry`. Visual: file icon + name + size, blue bar (upload), green bar (parsing), success checkmark, or red error text + retry.

**ColumnSelector** — props `{title, columns: ColumnInfo[], selected: string[]}`, emits `toggle`. Search box if `columns.length > 8`. Select-All / Clear actions. Each row: checkbox + name + null-pct badge (color-graded).

**DataPreview** — props `{columns, rows, totalRows, nullPcts?}`. Sticky header, monospace cells, scroll body.

**DimensionFilter** — props `{dimensionValues, selectedDimensions, filters}`, emits `update-filter`. Per-dimension group with mode toggle (List ↔ Pattern):
- List mode: checkboxes (first 20 values).
- Pattern mode: comma-separated glob (`*`) input, debounced 400 ms, case-insensitive, displays match count.

**AggregationControl** — props `{value}`, emits `update`. Renders option buttons.

**KPIEditor** — props `{kpis, selectedMetrics, availableColumns, sessionId}`, emits `add, remove, toggle, save`. List with row-level edit/remove. Modal (Teleport to body) for add/edit, fields:
- Name (must be unique vs metrics + KPIs).
- Formula (textarea + autocomplete suggestions, debounced server-side validation `POST /datasets/{sid}/kpis/validate`).
- Keyboard nav: ↑/↓ in suggestion dropdown; Enter/Tab to insert; Esc to close.
- Save persists via `dataset.saveKPIs`.

**AppHeader** — logo + 5-step breadcrumb (numbered, completed=green ✓, active=indigo, future=disabled). Clicking a completed step navigates back to it. Right side: theme toggle (sun/moon, swaps `data-theme` attribute on `<html>`), Download Parquet button (when sessionId), Clear button (calls `deleteSession`, clears sessionStorage with prefix `*:{sessionId}`, resets all stores, navigates to `/upload`).

**ModelCard** — props `{model, compatible, reason?, selected, condensed?}`, emits `select, proceed`.
- Full layout (≈280 px width): icon, name, description (3-line clamp), meta row (min points, seasonality req), badges (GPU, Foundation, Multivariate), incompatibility warning, selected ✓ overlay.
- Condensed layout (≈220 px): tighter row.
- Single click → select; double click → select + proceed.

**ResultsChart** — props `{chartData, results, anomalies?, regions?, thresholdValue?, loading, showFitLine?}`. Exposes `zoomToRange(start,end)`, `resetZoom()`, `getZoomRange()`, `restoreZoom(range)`.

ECharts config:
- Two grids (top 60% values; bottom 40% scores) when `results.scores` present.
- Series in main grid: line per metric (solid), pre-transform "(original)" line dashed, fit/forecast overlay dashed, scatter for anomaly points (severity color: high=#ef4444, medium=#f97316, low=#fbbf24).
- Score grid: line per metric (filled area), `markLine` at `thresholdValue` (horizontal).
- Region overlays: shaded background `markArea` per region, severity-colored.
- X-axis time, sync across grids; legend toggleable; dataZoom slider + inside; toolbox (drag-zoom, undo); tooltip cross-hair multi-axis; theme-aware colors (read from CSS vars).

**ParamPanel** — props/emits as listed in section 10.5 plus `availableMetrics`. Sections (collapsible):
1. **Model Parameters** — render generically by `param.type` (int/float/bool/select); slider where `min/max` available, else number input.
2. **Anomaly Detection** — radio for detector type, slider for threshold, score-stats display (min, p50, p90, p95, p99, max from `results.scores`).
3. **Data Preprocessing** — smoothing slider, infill select, transform checkboxes.
4. **Filtering** — persistence damping slider [0,1], min anomaly points spinner [≥1], volume gate metric select + threshold slider.
5. **Actions** — Run, Reset Defaults.

**AnomalyTable** — props `{regions, explanations: Map<string,string>}`, emits `region-click(start,end)`. Sortable columns: expand chevron, start, severity badge, metric, avg score, point count. Row expansion shows the explanation. Header summary chips (total / high / med / low).

**AnalysisProgress** — props `{progress, stage}`. Progress bar + stage label + percentage.

### 10.9 Utils

**color.ts**:
```ts
const SERIES_PALETTE = ['#6366f1','#22d3ee','#f97316','#10b981','#f43f5e',
                       '#a855f7','#fbbf24','#14b8a6','#d946ef','#0ea5e9']
getSeriesColor(i) // SERIES_PALETTE[i % palette.length]
getSeverityColor('high'|'medium'|'low'|other) // ef4444 / f97316 / fbbf24 / muted
getSeverityBgColor(...) // 0.15 alpha bg variants
```

**constants.ts**:
```ts
AGGREGATION_OPTIONS = [
 {value:'raw',label:'Raw'}, {value:'15min',label:'15 min'},
 {value:'30min',label:'30 min'}, {value:'1h',label:'1 hour'},
 {value:'4h',label:'4 hours'}, {value:'1d',label:'1 day'}]
CHUNK_SIZE = 2*1024*1024
MAX_CHART_POINTS = 3000
```

**formatters.ts**: `formatBytes(b)` (B/KB/MB), `formatNumber(n, dp)` with K/M suffix, `formatPercent(v, dp)`, `formatTimestamp(ts)` `Mon DD, HH:mm`.

**explainer.ts** — `explainRegion(region: AnomalyRegion, seriesData: SeriesData[]): string`.
Strategy:
1. Locate the region's points in the relevant series.
2. Compute baseline = mean of values outside the region; pct change vs baseline; std and Spearman trend (rank correlation of values vs index).
3. Classify pattern using thresholds:
   - `single_outlier` (point_count==1)
   - `spike_up` / `spike_down`
   - `volatility_increase` (std vastly above baseline)
   - `gradual_drift_up` / `gradual_drift_down` (trend > 0.5 / < −0.5)
   - `level_shift_up` / `level_shift_down`
   - `sustained_deviation`
4. Return a human-readable sentence (e.g., `"Metric spiked to 125.3 around Jan 15, 250% above the baseline of 50.1."`).

### 10.10 Styles

**`styles/variables.css`** — design tokens. Default `:root` and `[data-theme="dark"]`:
- bg-primary `#0f1117`, bg-surface `#1a1d27`, bg-elevated `#242836`
- text-primary `#e4e6f0`, text-secondary `#8b8fa3`, text-muted `#5c5f72`
- accent-primary `#6366f1` (indigo), accent-secondary `#22d3ee` (cyan)
- success `#10b981`, warning `#fbbf24`, error `#ef4444`
- border-primary `#2d3348`, border-subtle `#232738`
- 10-color chart palette: `#6366f1, #22d3ee, #f97316, #10b981, #f43f5e, #a855f7, #fbbf24, #14b8a6, #d946ef, #0ea5e9`

`[data-theme="light"]`: bg-primary `#f8f9fb`, surface `#ffffff`, elevated `#f1f3f7`; text-primary `#111827`, text-secondary `#4b5563`, text-muted `#9ca3af`; border-primary `#d1d5db`, border-subtle `#e5e7eb`; same accent colors.

Spacing: `--space-xs=4px, sm=8px, md=16px, lg=24px, xl=32px, 2xl=48px`.
Radius: `--radius-sm=6px, md=8px, lg=12px, xl=16px`.
Fonts: `Inter` body, `JetBrains Mono` mono. Header height `56px`. Transitions: fast `150ms`, normal `250ms`, slow `400ms`.

**`styles/base.css`**: global reset, 14 px base font, smooth scroll. Button helpers: `.btn`, `.btn-primary` (indigo), `.btn-secondary`, `.btn-ghost`, `.btn-sm`, `.btn-xs`. Utility classes `.card`, `.card-elevated`, `.label`, `.mono`, `.text-muted`, `.text-secondary`. Inputs/selects/textareas inherit font, bg-elevated, border-primary, focus = border-focus indigo. Custom scrollbar 8 px, thumb border-primary.

**`styles/transitions.css`**:
- `.fade-enter/leave-active { transition: opacity var(--transition-normal); }` opacity 0.
- `.slide-up-*` translateY ±12 px.
- `.slide-right-*` translateX ±20 px.

---

## 11. Persisted State

Two `sessionStorage` keys per session (cleared by Clear button):
- `dataset-selections:{sessionId}` → `{metrics, dimensions, dimensionFilters, aggregation, kpiDefinitions}`
- `model-selection:{sessionId}` → `{selectedModelId, params, detectorType, detectorThreshold, smoothingWindow, transforms, infill, scorerId, persistenceDamping, minAnomalyPoints, volumeGateMetric, volumeGateThreshold, showFitLine}`

Restoration happens on view mount before the chart/compatibility loads.

---

## 12. Build & Run

### Native dev
```bash
# Backend
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[torch,peer]"
uvicorn app.main:app --reload --port 8001

# Frontend
cd frontend && npm install && npm run dev   # port 5173
```
Or `./dev.sh` to run both with port cleanup.

### Production via Docker
```bash
docker compose up --build      # http://localhost:8090
```
The container serves the built Vue SPA from FastAPI at `/`. The `app_data` volume persists uploads/parsed/results/HF cache across restarts.

### Tests / lint
- Backend: `pytest` in `backend/`, `ruff check app/`
- Frontend: `npm run lint`, `npm run type-check` (`vue-tsc --noEmit`)

---

## 13. Environment Variables

| Name | Default | Effect |
|---|---|---|
| `DAD_SESSION_TTL_HOURS` | 24 | Background cleanup window |
| `DAD_MAX_UPLOAD_SIZE_MB` | 500 | Reject larger uploads at /upload/init |
| `DAD_MAX_CHART_POINTS` | 3000 | Default `max_points` for /viz/timeseries |
| `DAD_CHUNK_SIZE_BYTES` | 2 MB | Chunk size hint |
| `DAD_CORS_ORIGINS` | localhost:5173, 3000 | Comma-separated list (set as JSON if needed) |
| `HF_HUB_CACHE` | `/app/data/hf_cache` | HuggingFace model cache dir |

---

## 14. Acceptance Criteria

The rebuilt app is correct if all of the below hold:

1. **Health**: `curl /api/health` → `{"status":"ok",...}`.
2. **Upload**: Uploading a 100 MB CSV with chunked client succeeds, WebSocket emits `progress` events, status transitions `uploading → parsing → ready`. Original CSV is deleted; parquet exists with snappy compression.
3. **Column classification** matches section 7.3 exactly on representative telecom CSVs (NODE_NAME parsed into 4 sub-columns when ≥80 % match the 11-char pattern).
4. **KPI**: `(VS.Success / VS.Attempts) * 100` validates and computes per-row after aggregation. Dot/space column names get auto-backticked. Unknown variable yields `"Unrecognised variable(s): X"`.
5. **Aggregation**: 1h aggregation across multiple NODE_NAME groups yields `groupby(dim).resample('1h').sum()` semantics.
6. **Models**: `GET /api/models/` returns ≥ 60 models with the parameters described in section 8.1. Frontend renders forms generically.
7. **Compatibility**: peer models incompatible without dimensions, multivariate restrictions enforced, min_data_points respected.
8. **Detection**: Running `isolation_forest` on a 1 K-row metric returns DartsAnomalyResult with anomalies, scores, summary, regions; quantile detector at 0.95 yields top 5 % flagged.
9. **Threshold slider**: Moving the slider in AnalysisView changes `effectiveAnomalies` count without a server roundtrip.
10. **Persistence damping**: `persistence_damping=0.5, min_anomaly_points=3` filters out single-point regions and boosts severity of long ones per `score × (1 + 0.5 × log2(n))`.
11. **Volume gate**: anomalies whose timestamp has volume_metric < threshold are removed.
12. **Visualization**: `/viz/timeseries` returns ≤ `max_points` points using LTTB; `original_series` is populated when transforms are applied.
13. **Export**: `/viz/export-csv` streams a CSV with `ts_col + dimensions + metrics`, KPIs computed.
14. **Privacy**: DELETE `/datasets/{sid}` removes all three session dirs; cleanup scheduler fires every 30 min and removes sessions older than TTL.
15. **Frontend**: All 5 views render, breadcrumb navigation works, Clear button wipes server + sessionStorage, theme toggle persists in `data-theme` attribute.
16. **WS**: AnalysisView reconnects on close; UploadView falls back to polling every 2 s.

---

## 15. Quick Reference — File-by-file Checklist

Backend files to implement (each documented above):
- `app/main.py`, `app/config.py`
- `app/api/{upload,datasets,models,visualization,ws}.py`
- `app/models/{enums,schemas}.py`
- `app/services/{session_manager,csv_parser,column_classifier,dimension_parser,aggregator,kpi_computer,downsampler}.py`
- `app/services/darts/{registry,compatibility,runner}.py`
- `app/storage/{parquet_store,result_cache}.py`
- `app/utils/{cleanup,progress}.py`

Frontend files:
- `src/{main.ts, App.vue}`
- `src/router/index.ts`
- `src/api/{client,types,upload,datasets,models,analysis}.ts`
- `src/stores/{upload,dataset,models,analysis}.ts`
- `src/views/{UploadView,PreviewView,ConfigureView,ModelSelectView,AnalysisView}.vue`
- `src/components/upload/{FileDropZone,UploadProgress}.vue`
- `src/components/dataset/{ColumnSelector,DataPreview,DimensionFilter,AggregationControl,KPIEditor}.vue`
- `src/components/layout/AppHeader.vue`
- `src/components/models/ModelCard.vue`
- `src/components/analysis/{ResultsChart,ParamPanel,AnomalyTable,AnalysisProgress}.vue`
- `src/composables/useWebSocket.ts`
- `src/utils/{color,constants,formatters,explainer}.ts`
- `src/styles/{variables,base,transitions}.css`

Container/dev:
- `Dockerfile`, `docker-compose.yml`, `dev.sh`
- `backend/pyproject.toml`, `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`

---

# Appendix A — Verbatim Small-File Contents

These files are small but spec-critical; reproduce them literally (modulo formatting).

### A.1 `frontend/index.html`
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Anomaly Detection Playground</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

### A.2 `frontend/tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src/**/*.ts", "src/**/*.vue", "env.d.ts"],
  "exclude": ["node_modules"]
}
```

### A.3 `frontend/vite.config.ts`
```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': resolve(__dirname, 'src') } },
  server: {
    port: 5173,
    allowedHosts: ['anom.roxb.in'],
    proxy: {
      '/api': { target: 'http://localhost:8001', changeOrigin: true, ws: true },
    },
  },
})
```

### A.4 `frontend/src/main.ts`
```ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './styles/base.css'
import './styles/transitions.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

### A.5 `frontend/src/App.vue`
```vue
<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
</script>

<template>
  <AppHeader />
  <main class="app-main">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </main>
</template>

<style scoped>
.app-main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
</style>
```

### A.6 `frontend/src/router/index.ts`
```ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/upload' },
    { path: '/upload',                name: 'upload',    component: () => import('@/views/UploadView.vue') },
    { path: '/preview/:sessionId',    name: 'preview',   component: () => import('@/views/PreviewView.vue'),    props: true },
    { path: '/configure/:sessionId',  name: 'configure', component: () => import('@/views/ConfigureView.vue'),  props: true },
    { path: '/models/:sessionId',     name: 'models',    component: () => import('@/views/ModelSelectView.vue'),props: true },
    { path: '/analysis/:sessionId',   name: 'analysis',  component: () => import('@/views/AnalysisView.vue'),   props: true },
  ],
})
export default router
```

### A.7 `frontend/src/api/client.ts`
```ts
import axios from 'axios'
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})
export default apiClient
```

### A.8 `frontend/src/api/types.ts` (canonical TS shapes)
```ts
export interface UploadInitRequest { filename: string; file_size: number; chunk_size?: number; file_type?: 'csv' | 'parquet' }
export interface UploadInitResponse { session_id: string; upload_id: string; total_chunks: number }
export interface UploadStatusResponse {
  upload_id: string; status: 'uploading' | 'parsing' | 'ready' | 'error'
  chunks_received: number; total_chunks: number; parsing_progress: number; error: string | null
}
export interface ColumnInfo { name: string; dtype: string; null_count: number; null_pct: number; sample_values: (string|number|null)[] }
export interface KPIDefinition { name: string; formula: string; description: string }
export interface DatasetMetadata {
  session_id: string; filename: string; row_count: number; time_range: [string, string]
  timestamp_column: string; dimension_columns: ColumnInfo[]; metric_columns: ColumnInfo[]
  skipped_header_lines: number; kpi_definitions?: KPIDefinition[]
}
export interface DimensionValues { column: string; values: string[]; count: number }
export type AggregationLevel = 'raw' | '15min' | '30min' | '1h' | '4h' | '1d'
export interface ModelParam {
  name: string; label: string; type: 'int'|'float'|'bool'|'select'
  default: number|boolean|string; min?: number; max?: number; step?: number
  options?: string[]; description: string
}
export interface ModelInfo {
  id: string; name: string; description: string; category: 'scorer'|'forecast'
  supports_multivariate: boolean; min_data_points: number
  requires_seasonality: boolean; requires_dimensions: boolean
  gpu_accelerated: boolean; foundation: boolean; params: ModelParam[]
}
export interface ModelCompatibility { model_id: string; compatible: boolean; reason: string|null }
export interface CompatibilityResponse { models: ModelCompatibility[] }
export type TransformId = 'winsorize'|'log'|'boxcox'|'diff'|'scale_standard'|'scale_minmax'
export type InfillMethod = 'none'|'linear'|'time'|'ffill'|'zero'
export interface DartsDetectionConfig {
  model_id: string; metrics: string[]
  dimensions?: string[]|null; dimension_filters?: Record<string,string[]>|null
  aggregation: AggregationLevel; params: Record<string, number|boolean|string>
  detector_type: 'quantile'|'threshold'|'iqr'; detector_threshold: number
  smoothing_window: number; transforms: TransformId[]; infill: InfillMethod
  scorer_id: string; random_seed: number|null
  persistence_damping: number; min_anomaly_points: number
  volume_gate_metric: string|null; volume_gate_threshold: number
}
export interface DartsAnomalyPoint {
  timestamp: string; metric: string; value: number; score: number
  is_anomaly: boolean; severity: 'low'|'medium'|'high'
  dimension_values?: Record<string,string>|null
}
export interface ForecastPoint { timestamp: string; metric: string; predicted: number; actual: number; dimension_values?: Record<string,string>|null }
export interface AnomalyRegion {
  start: string; end: string; metric: string; severity: 'low'|'medium'|'high'
  avg_score: number; point_count: number; dimension_values?: Record<string,string>|null
}
export interface AnomalySummary {
  total_points_analyzed: number; total_anomalies: number; total_regions: number
  by_severity: Record<string, number>; by_metric: Record<string, number>
}
export interface DartsAnomalyResult {
  run_id: string; config: DartsDetectionConfig
  anomalies: DartsAnomalyPoint[]
  scores: Array<{ timestamp: string; metric: string; score: number }>   // <— exact shape
  forecast: ForecastPoint[]|null; summary: AnomalySummary; regions: AnomalyRegion[]
}
export interface SeriesData { name: string; timestamps: string[]; values: (number|null)[] }
export interface TimeSeriesRequest {
  metrics: string[]; dimensions?: string[]|null; dimension_filters?: Record<string,string[]>|null
  aggregation: AggregationLevel; time_start?: string|null; time_end?: string|null
  max_points?: number; smoothing_window?: number; transforms?: TransformId[]; infill?: InfillMethod
}
export interface TimeSeriesResponse { series: SeriesData[]; original_series?: SeriesData[]|null; total_raw_points: number; downsampled: boolean }
export interface WebSocketMessage { type: 'progress'|'complete'|'error'|'ping'; stage?: string; progress?: number; detail?: string; run_id?: string }
```

### A.9 `frontend/src/utils/color.ts`
```ts
const CHART_PALETTE = [
  '#6366f1','#22d3ee','#f97316','#10b981','#f43f5e',
  '#a78bfa','#fb923c','#34d399','#e879f9','#38bdf8',
]
export function getSeriesColor(i: number): string { return CHART_PALETTE[i % CHART_PALETTE.length] }
export function getSeverityColor(s: string): string {
  switch (s) {
    case 'high':   return '#ef4444'
    case 'medium': return '#f97316'
    case 'low':    return '#fbbf24'
    default:       return '#6b7280'
  }
}
export function getSeverityBgColor(s: string): string {
  switch (s) {
    case 'high':   return 'rgba(239, 68, 68, 0.25)'
    case 'medium': return 'rgba(249, 115, 22, 0.20)'
    case 'low':    return 'rgba(251, 191, 36, 0.15)'
    default:       return 'rgba(107, 114, 128, 0.10)'
  }
}
```

### A.10 `frontend/src/utils/constants.ts`
```ts
export const AGGREGATION_OPTIONS = [
  { value: 'raw', label: 'Raw (5 min)' },
  { value: '15min', label: '15 Minutes' },
  { value: '30min', label: '30 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: '1 Day' },
] as const

export const CHUNK_SIZE = 2 * 1024 * 1024
export const MAX_CHART_POINTS = 3000
```

### A.11 `frontend/src/utils/formatters.ts`
```ts
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024, sizes = ['B','KB','MB','GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}
export function formatNumber(n: number, decimals = 1): string {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(decimals)}M`
  if (Math.abs(n) >= 1_000)     return `${(n / 1_000).toFixed(decimals)}K`
  return n.toFixed(decimals)
}
export function formatPercent(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`
}
export function formatTimestamp(ts: string): string {
  return new Date(ts).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}
```

### A.12 `frontend/src/styles/variables.css`
```css
:root, [data-theme="dark"] {
  --bg-primary: #0f1117; --bg-surface: #1a1d27; --bg-elevated: #242836; --bg-hover: #2a2f3f;
  --border-primary: #2d3348; --border-subtle: #232738; --border-focus: #6366f1;
  --text-primary: #e4e6f0; --text-secondary: #8b8fa3; --text-muted: #5c5f72; --text-inverse: #0f1117;
  --accent-primary: #6366f1; --accent-primary-hover: #7577f5;
  --accent-secondary: #22d3ee; --accent-secondary-hover: #45ddf2;
  --color-success: #10b981; --color-warning: #fbbf24; --color-error: #ef4444; --color-info: #6366f1;
  --anomaly-low-bg: rgba(251,191,36,0.12); --anomaly-low-border: #fbbf24;
  --anomaly-medium-bg: rgba(249,115,22,0.16); --anomaly-medium-border: #f97316;
  --anomaly-high-bg: rgba(239,68,68,0.20);  --anomaly-high-border: #ef4444;
  --chart-1:#6366f1; --chart-2:#22d3ee; --chart-3:#f97316; --chart-4:#10b981;
  --chart-5:#f43f5e; --chart-6:#a78bfa; --chart-7:#fb923c; --chart-8:#34d399;
  --space-xs:4px; --space-sm:8px; --space-md:16px; --space-lg:24px; --space-xl:32px; --space-2xl:48px;
  --radius-sm:6px; --radius-md:8px; --radius-lg:12px; --radius-xl:16px;
  --shadow-sm:0 1px 2px rgba(0,0,0,0.3); --shadow-md:0 4px 12px rgba(0,0,0,0.4); --shadow-lg:0 8px 24px rgba(0,0,0,0.5);
  --transition-fast: 150ms ease; --transition-normal: 250ms ease; --transition-slow: 400ms ease;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  --header-height: 56px; --sidebar-width: 320px;
}
[data-theme="light"] {
  --bg-primary:#f8f9fb; --bg-surface:#ffffff; --bg-elevated:#f1f3f7; --bg-hover:#e8ebf0;
  --border-primary:#d1d5db; --border-subtle:#e5e7eb;
  --text-primary:#111827; --text-secondary:#4b5563; --text-muted:#9ca3af; --text-inverse:#ffffff;
  --shadow-sm:0 1px 2px rgba(0,0,0,0.06); --shadow-md:0 4px 12px rgba(0,0,0,0.08); --shadow-lg:0 8px 24px rgba(0,0,0,0.12);
}
```

### A.13 `frontend/src/styles/base.css` (essential rules)
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
@import './variables.css';

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 14px; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
body { font-family: var(--font-sans); background: var(--bg-primary); color: var(--text-primary); line-height: 1.5; min-height: 100vh; }
#app { min-height: 100vh; display: flex; flex-direction: column; }

a { color: var(--accent-secondary); text-decoration: none; transition: color var(--transition-fast); }
a:hover { color: var(--accent-secondary-hover); }
button { font-family: inherit; cursor: pointer; border: none; background: none; color: inherit; }
input, select, textarea {
  font-family: inherit; font-size: inherit; color: var(--text-primary);
  background: var(--bg-elevated); border: 1px solid var(--border-primary);
  border-radius: var(--radius-md); padding: var(--space-sm) var(--space-md); outline: none;
  transition: border-color var(--transition-fast);
}
input:focus, select:focus, textarea:focus { border-color: var(--border-focus); }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border-primary); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

.card { background: var(--bg-surface); border: 1px solid var(--border-primary); border-radius: var(--radius-lg); padding: var(--space-lg); }
.card-elevated { background: var(--bg-elevated); border: 1px solid var(--border-primary); border-radius: var(--radius-lg); padding: var(--space-lg); box-shadow: var(--shadow-md); }

.btn { display: inline-flex; align-items: center; justify-content: center; gap: var(--space-sm);
       padding: var(--space-sm) var(--space-lg); border-radius: var(--radius-md);
       font-weight: 500; font-size: 0.875rem; transition: all var(--transition-fast); white-space: nowrap; }
.btn-primary { background: var(--accent-primary); color: white; }
.btn-primary:hover { background: var(--accent-primary-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: var(--bg-elevated); color: var(--text-primary); border: 1px solid var(--border-primary); }
.btn-secondary:hover { background: var(--bg-hover); border-color: var(--text-muted); }
.btn-ghost { color: var(--text-secondary); }
.btn-ghost:hover { color: var(--text-primary); background: var(--bg-elevated); }

.label { display:block; font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-secondary); margin-bottom:var(--space-xs); }
.mono { font-family: var(--font-mono); }
.text-muted { color: var(--text-muted); }
.text-secondary { color: var(--text-secondary); }
```

### A.14 `frontend/src/styles/transitions.css`
```css
.fade-enter-active, .fade-leave-active { transition: opacity var(--transition-normal); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active, .slide-up-leave-active { transition: all var(--transition-normal); }
.slide-up-enter-from { opacity: 0; transform: translateY(12px); }
.slide-up-leave-to   { opacity: 0; transform: translateY(-12px); }

.slide-right-enter-active, .slide-right-leave-active { transition: all var(--transition-normal); }
.slide-right-enter-from { opacity: 0; transform: translateX(-20px); }
.slide-right-leave-to   { opacity: 0; transform: translateX(20px); }
```

### A.15 `backend/app/storage/parquet_store.py`
```python
import logging
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from ..config import settings

logger = logging.getLogger(__name__)


class ParquetStore:
    def write(self, session_id: str, df: pd.DataFrame):
        out = settings.parsed_dir / session_id
        out.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out / "data.parquet", engine="pyarrow", compression="snappy", index=False)

    def read(self, session_id: str, columns: list[str] | None = None, limit: int | None = None) -> pd.DataFrame:
        path = settings.parsed_dir / session_id / "data.parquet"
        if not path.exists():
            raise FileNotFoundError(f"No parsed data for session {session_id}")
        if columns:
            valid = set(pq.read_schema(path).names)
            invalid = [c for c in columns if c not in valid]
            if invalid:
                logger.warning("Requested columns not in Parquet: %s (available: %s)", invalid, list(valid)[:20])
                columns = [c for c in columns if c in valid]
                if not columns:
                    raise FileNotFoundError("None of the requested columns exist in the dataset")
        df = pd.read_parquet(path, engine="pyarrow", columns=columns)
        if limit is not None:
            df = df.head(limit)
        return df

    def exists(self, session_id: str) -> bool:
        return (settings.parsed_dir / session_id / "data.parquet").exists()


parquet_store = ParquetStore()
```

### A.16 `backend/app/storage/result_cache.py`
```python
import json
from pathlib import Path
from ..config import settings
from ..models.schemas import DartsAnomalyResult


class ResultCache:
    def save(self, session_id: str, run_id: str, result: DartsAnomalyResult):
        d = settings.results_dir / session_id
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{run_id}.json").write_text(result.model_dump_json(indent=2))

    def load(self, session_id: str, run_id: str) -> DartsAnomalyResult | None:
        p = settings.results_dir / session_id / f"{run_id}.json"
        if not p.exists():
            return None
        return DartsAnomalyResult(**json.loads(p.read_text()))

    def exists(self, session_id: str, run_id: str) -> bool:
        return (settings.results_dir / session_id / f"{run_id}.json").exists()


result_cache = ResultCache()
```

### A.17 `backend/app/utils/cleanup.py`
```python
import json, shutil
from datetime import datetime, timezone, timedelta
from ..config import settings


def cleanup_expired_sessions():
    ttl = timedelta(hours=settings.session_ttl_hours)
    now = datetime.now(timezone.utc)
    for base in [settings.upload_dir, settings.parsed_dir, settings.results_dir]:
        if not base.exists():
            continue
        for sd in base.iterdir():
            if not sd.is_dir():
                continue
            meta = sd / "metadata.json"
            if meta.exists():
                try:
                    m = json.loads(meta.read_text())
                    created = datetime.fromisoformat(m.get("created_at", ""))
                    if now - created > ttl:
                        shutil.rmtree(sd, ignore_errors=True)
                except (json.JSONDecodeError, ValueError, KeyError):
                    mtime = datetime.fromtimestamp(meta.stat().st_mtime, tz=timezone.utc)
                    if now - mtime > ttl:
                        shutil.rmtree(sd, ignore_errors=True)
            else:
                try:
                    mtime = datetime.fromtimestamp(sd.stat().st_mtime, tz=timezone.utc)
                    if now - mtime > ttl:
                        shutil.rmtree(sd, ignore_errors=True)
                except OSError:
                    pass
```

### A.18 `backend/app/utils/progress.py`
```python
import asyncio, json
from collections import defaultdict
from typing import Any


class ProgressBroadcaster:
    def __init__(self):
        self._connections: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, session_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._connections[session_id].append(q)
        return q

    def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        if session_id in self._connections:
            self._connections[session_id] = [q for q in self._connections[session_id] if q is not queue]
            if not self._connections[session_id]:
                del self._connections[session_id]

    async def broadcast(self, session_id: str, event_type: str, data: dict[str, Any]):
        msg = json.dumps({"type": event_type, **data})
        for q in self._connections.get(session_id, []):
            await q.put(msg)

    async def send_progress(self, session_id: str, stage: str, progress: float, detail: str = ""):
        await self.broadcast(session_id, "progress", {
            "stage": stage, "progress": round(progress, 1), "detail": detail,
        })

    async def send_error(self, session_id: str, error: str):
        await self.broadcast(session_id, "error", {"detail": error})

    async def send_complete(self, session_id: str, stage: str, data: dict[str, Any] | None = None):
        await self.broadcast(session_id, "complete", {"stage": stage, **(data or {})})


progress_broadcaster = ProgressBroadcaster()
```

---

# Appendix B — Backend Detection Builders & Pipelines (concrete code patterns)

> These patterns translate directly from the working implementation. Every model in section 8 must be built using the corresponding pattern below.

### B.1 GPU accelerator selection (cached)
```python
_ACCELERATOR: str | None = None
def _cached_accelerator() -> str:
    global _ACCELERATOR
    if _ACCELERATOR is not None:
        return _ACCELERATOR
    try:
        import torch
        if torch.backends.mps.is_available():
            _ACCELERATOR = "mps"; return _ACCELERATOR
        if torch.cuda.is_available():
            _ACCELERATOR = "cuda"; return _ACCELERATOR
    except (ImportError, AttributeError):
        pass
    _ACCELERATOR = "cpu"
    return _ACCELERATOR
```

`pl_trainer_kwargs={"accelerator": _cached_accelerator(), "enable_progress_bar": False}` is passed to all Lightning-trained DL forecasters.

### B.2 Random seed propagation
At the top of `run_darts_detection`:
```python
seed = getattr(config, "random_seed", None)
if seed is not None:
    import random; random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass
```

### B.3 Param coercion helpers
```python
# Comma-separated → list[int] (autoencoder/vae hidden_neurons)
hidden_str = str(params.get("hidden_neurons", "64,32,32,64"))
hidden = [int(x.strip()) for x in hidden_str.split(",")]
# VAE encoder/decoder split at midpoint
mid = len(hidden) // 2; encoder_list = hidden[:mid]; decoder_list = hidden[mid:]

# Theta seasonality string → enum
from darts.utils.utils import SeasonalityMode
mode_map = {
  "multiplicative": SeasonalityMode.MULTIPLICATIVE,
  "additive":       SeasonalityMode.ADDITIVE,
  "none":           SeasonalityMode.NONE,
}
season_mode = mode_map.get(str(params.get("season_mode", "multiplicative")),
                           SeasonalityMode.MULTIPLICATIVE)

# Prophet seasonality flags pass through "auto" verbatim or convert to bool
def _prophet_bool(v):
    return "auto" if v == "auto" else (v == "true" or v is True)
```

### B.4 `build_scorer(model_id, params)` — model factory excerpts

```python
from darts.ad.scorers import KMeansScorer, PyODScorer, WassersteinScorer
from pyod.models.iforest import IForest
from pyod.models.lof import LOF
from pyod.models.ecod import ECOD
from pyod.models.copod import COPOD
from pyod.models.hbos import HBOS
from pyod.models.knn import KNN
from pyod.models.ocsvm import OCSVM
from pyod.models.inne import INNE
from pyod.models.loda import LODA
from pyod.models.cblof import CBLOF
from pyod.models.rod import ROD
from pyod.models.abod import ABOD
from pyod.models.sos import SOS
from pyod.models.lscp import LSCP
from pyod.models.sod import SOD
from pyod.models.vae import VAE
from pyod.models.pca import PCA
from pyod.models.mcd import MCD
from pyod.models.deep_svdd import DeepSVDD
from pyod.models.auto_encoder import AutoEncoder

window = max(1, int(params.get("window", 10)))
contam = float(params.get("contamination", 0.1))

# Native Darts scorers
"kmeans"       -> KMeansScorer(window=window, k=int(params["k"]))
"wasserstein"  -> WassersteinScorer(window=window)

# PyOD-wrapped scorers
"isolation_forest" -> PyODScorer(model=IForest(n_estimators=int(params["n_estimators"]), contamination=contam), window=window)
"lof"              -> PyODScorer(model=LOF(n_neighbors=int(params["n_neighbors"]), contamination=contam), window=window)
"ecod"             -> PyODScorer(model=ECOD(contamination=contam), window=window)
"copod"            -> PyODScorer(model=COPOD(contamination=contam), window=window)
"hbos"             -> PyODScorer(model=HBOS(n_bins=int(params["n_bins"]), contamination=contam), window=window)
"knn"              -> PyODScorer(model=KNN(n_neighbors=int(params["n_neighbors"]), contamination=contam), window=window)
"ocsvm"            -> PyODScorer(model=OCSVM(kernel=str(params["kernel"]), nu=contam), window=window)   # nu, not contamination
"inne"             -> PyODScorer(model=INNE(n_estimators=int(params["n_estimators"]), contamination=contam), window=window)
"loda"             -> PyODScorer(model=LODA(n_bins=int(params["n_bins"]), n_random_cuts=int(params["n_random_cuts"]), contamination=contam), window=window)
"cblof"            -> PyODScorer(model=CBLOF(n_clusters=int(params["n_clusters"]), alpha=float(params["alpha"]), contamination=contam), window=window)
"rod"              -> PyODScorer(model=ROD(contamination=contam), window=window)
"abod"             -> PyODScorer(model=ABOD(n_neighbors=int(params["n_neighbors"]), method=str(params["method"]), contamination=contam), window=window)
"sos"              -> PyODScorer(model=SOS(perplexity=float(params["perplexity"]), contamination=contam), window=window)
"lscp"             -> PyODScorer(model=LSCP(detector_list=[LOF(), IForest(), OCSVM()], contamination=contam), window=window)
"sod"              -> PyODScorer(model=SOD(n_neighbors=int(params["n_neighbors"]), ref_set=int(params["ref_set"]), contamination=contam), window=window)
"pca"              -> PyODScorer(model=PCA(n_components=int(params["n_components"]), contamination=contam), window=window)
"mcd"              -> PyODScorer(model=MCD(support_fraction=float(params["support_fraction"]), contamination=contam), window=window)
"deep_svdd"        -> PyODScorer(model=DeepSVDD(n_features=window, epochs=int(params["epochs"]), contamination=contam), window=window)
"autoencoder"      -> PyODScorer(model=AutoEncoder(hidden_neuron_list=hidden, epoch_num=int(params["epochs"]),
                                  dropout_rate=float(params["dropout_rate"]), contamination=contam), window=window)
"vae"              -> PyODScorer(model=VAE(encoder_neuron_list=hidden[:mid], decoder_neuron_list=hidden[mid:],
                                  latent_dim=int(params["latent_dim"]), epoch_num=int(params["epochs"]),
                                  contamination=contam), window=window)
```

### B.5 `build_residual_scorer(scorer_id, params)` — for forecast pipelines
```python
from darts.ad.scorers import DifferenceScorer, NormScorer

def build_residual_scorer(scorer_id, params, window=10):
    if scorer_id == "difference":   return DifferenceScorer()
    if scorer_id == "norm":         return NormScorer(ord=1, window=window)
    if scorer_id == "kmeans":       return KMeansScorer(window=window, k=int(params.get("scorer_k", 8)))
    if scorer_id == "wasserstein":  return WassersteinScorer(window=window)
    if scorer_id == "pyod_iforest": return PyODScorer(model=IForest(), window=window)
    if scorer_id == "pyod_lof":     return PyODScorer(model=LOF(), window=window)
    if scorer_id == "pyod_copod":   return PyODScorer(model=COPOD(), window=window)
    if scorer_id == "pyod_knn":     return PyODScorer(model=KNN(), window=window)
    return DifferenceScorer()  # fallback
```

`difference` and `norm` are parameter-free; for any other scorer call `scorer.fit_from_prediction(actual_ts, pred_ts)` before `score_from_prediction`.

### B.6 `build_forecast_model(model_id, params)` — local forecasters
```python
from darts.models import (
    ExponentialSmoothing, FFT, Theta, FourTheta, ARIMA, AutoARIMA,
    NaiveMean, NaiveSeasonal, NaiveDrift, NaiveMovingAverage, Croston, Prophet,
)
from darts.utils.utils import SeasonalityMode

"exponential_smoothing" -> ExponentialSmoothing(seasonal_periods=int(params["seasonal_periods"]))
"fft"                   -> FFT(nr_freqs_to_keep=int(params["nr_freqs_to_keep"]))
"theta"                 -> Theta(theta=float(params["theta"]), season_mode=season_mode)
"four_theta"            -> FourTheta(theta=float(params["theta"]), season_mode=season_mode)
"arima"                 -> ARIMA(p=int(params["p"]), d=int(params["d"]), q=int(params["q"]))
"auto_arima"            -> AutoARIMA(season_length=int(params["season_length"]))
"naive_mean"            -> NaiveMean()
"naive_seasonal"        -> NaiveSeasonal(K=int(params["K"]))
"naive_drift"           -> NaiveDrift()
"naive_moving_avg"      -> NaiveMovingAverage(input_chunk_length=int(params["input_chunk_length"]))
"croston"               -> Croston(version=str(params["version"]))
"prophet"               -> Prophet(growth=str(params["growth"]),
                                   changepoint_prior_scale=float(params["changepoint_prior_scale"]),
                                   seasonality_mode=str(params["seasonality_mode"]),
                                   seasonality_prior_scale=float(params["seasonality_prior_scale"]),
                                   daily_seasonality=_prophet_bool(params["daily_seasonality"]),
                                   weekly_seasonality=_prophet_bool(params["weekly_seasonality"]),
                                   yearly_seasonality=_prophet_bool(params["yearly_seasonality"]))
```

### B.7 `build_global_forecast_model(model_id, params)` — global forecasters / DL / foundation
```python
from darts.models import (
    LinearRegressionModel, RandomForest, LightGBMModel, XGBModel,
    NBEATSModel, NHiTSModel, TFTModel, DLinearModel, NLinearModel,
    TCNModel, TransformerModel, BlockRNNModel, TiDEModel, TSMixerModel,
    Chronos2Model, TimesFM2p5Model,
)

# Regression / ML
"linear_regression" -> LinearRegressionModel(lags=int(params["lags"]), output_chunk_length=1)
"random_forest"     -> RandomForest(lags=int(params["lags"]), output_chunk_length=1,
                                    n_estimators=int(params["n_estimators"]), max_depth=int(params["max_depth"]))
"lightgbm"          -> LightGBMModel(lags=..., output_chunk_length=1,
                                     n_estimators=..., max_depth=..., learning_rate=..., verbose=-1)
"xgboost"           -> XGBModel(lags=..., output_chunk_length=1,
                                n_estimators=..., max_depth=..., learning_rate=...)

# DL forecasters use this shared kwargs object
_dl_common = dict(
    input_chunk_length=int(params["input_chunk_length"]),
    output_chunk_length=1,
    n_epochs=int(params["n_epochs"]),
    batch_size=int(params["batch_size"]),
    dropout=float(params["dropout"]),
    optimizer_kwargs={"lr": float(params["learning_rate"])},
    pl_trainer_kwargs={"accelerator": _cached_accelerator(), "enable_progress_bar": False},
)
"nbeats"      -> NBEATSModel(**_dl_common, num_stacks=int(params["num_stacks"]))
"nhits"       -> NHiTSModel(**_dl_common, num_stacks=int(params["num_stacks"]))
"tft"         -> TFTModel(**_dl_common, hidden_size=int(params["hidden_size"]))
"dlinear"     -> DLinearModel(**_dl_common)
"nlinear"     -> NLinearModel(**_dl_common)
"tcn"         -> TCNModel(**_dl_common, num_filters=int(params["num_filters"]))
"transformer" -> TransformerModel(**_dl_common, d_model=int(params["d_model"]), nhead=int(params["nhead"]))
"block_rnn"   -> BlockRNNModel(**_dl_common, model=str(params["rnn_model"]), hidden_dim=int(params["hidden_dim"]))
"tide"        -> TiDEModel(**_dl_common, hidden_size=int(params["hidden_size"]))
"tsmixer"     -> TSMixerModel(**_dl_common, hidden_size=int(params["hidden_size"]))

# Foundation (output_chunk_length = FOUNDATION_CHUNK_SIZE = 128)
"chronos2" -> Chronos2Model(input_chunk_length=int(params["input_chunk_length"]),
                            output_chunk_length=FOUNDATION_CHUNK_SIZE,
                            hub_model_name=str(params["hub_model_name"]))
"timesfm"  -> TimesFM2p5Model(input_chunk_length=int(params["input_chunk_length"]),
                              output_chunk_length=FOUNDATION_CHUNK_SIZE)
```

### B.8 Detector wrapping
```python
from darts.ad.detectors import QuantileDetector, ThresholdDetector, IQRDetector

def build_detector(detector_type: str, threshold: float):
    if detector_type == "threshold": return ThresholdDetector(high_threshold=threshold)
    if detector_type == "iqr":       return IQRDetector(scale=threshold)
    return QuantileDetector(high_quantile=min(threshold, 0.999))

def _fit_and_detect(detector, scores_ts):
    if hasattr(detector, "fit"):
        detector.fit(scores_ts)
    return detector.detect(scores_ts)
```

### B.9 `_df_to_timeseries(df, ts_col, value_cols)`
```python
from darts import TimeSeries

def _df_to_timeseries(df, ts_col, value_cols):
    sub = df[[ts_col] + value_cols].copy().set_index(ts_col).sort_index()
    if sub.index.duplicated().any():
        sub = sub.groupby(sub.index).mean()
    freq = pd.infer_freq(sub.index)
    if freq is None and len(sub) > 2:
        diffs = sub.index.to_series().diff().dropna()
        diffs = diffs[diffs > pd.Timedelta(0)]
        if len(diffs) > 0:
            sub = sub.asfreq(diffs.median())
    elif freq:
        sub = sub.asfreq(freq)
    sub = sub.interpolate(method="time", limit=5).ffill().bfill()
    return TimeSeries.from_dataframe(sub, value_cols=value_cols, fill_missing_dates=True)
```

### B.10 Scorer pipeline (canonical body)
```python
def _run_scorer_pipeline(df, ts_col, metric_cols, config, anomaly_points, all_scores,
                         all_forecast_points=None, progress_cb=None):
    window = max(1, int(config.params.get("window", 10)))
    series = _df_to_timeseries(df, ts_col, metric_cols)
    if _cached_accelerator() == "mps":
        series = series.astype(np.float32)

    scorer = build_scorer(config.model_id, config.params)
    scorer.fit(series)
    scores_ts = scorer.score(series)

    detector = build_detector(config.detector_type, config.detector_threshold)
    binary_ts = _fit_and_detect(detector, scores_ts)

    scores_df = scores_ts.to_dataframe()
    binary_df = binary_ts.to_dataframe()
    orig_df   = series.to_dataframe()

    score_values = scores_df.values.flatten()
    score_values = score_values[~np.isnan(score_values)]
    threshold = float(np.quantile(score_values, min(config.detector_threshold, 0.999))) \
                if len(score_values) else 1.0

    for ts_idx in scores_df.index:
        ts_str = str(ts_idx)
        for i, metric in enumerate(metric_cols):
            sc = scores_df.columns[min(i, len(scores_df.columns)-1)]
            bc = binary_df.columns[min(i, len(binary_df.columns)-1)]
            score_val = float(scores_df.loc[ts_idx, sc])
            if math.isnan(score_val): score_val = 0.0
            actual_val = float(orig_df.loc[ts_idx, metric]) if ts_idx in orig_df.index else 0.0
            if math.isnan(actual_val): actual_val = 0.0
            is_anom = bool(binary_df.loc[ts_idx, bc]) if ts_idx in binary_df.index else False

            all_scores.append({"timestamp": ts_str, "metric": metric, "score": round(score_val, 6)})
            if is_anom:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str, metric=metric, value=round(actual_val, 6),
                    score=round(score_val, 6), is_anomaly=True,
                    severity=_classify_severity(score_val, threshold),
                ))

    # Optional fitted-baseline output (interpolating past anomalies for visual fit line)
    if all_forecast_points is not None:
        anomaly_ts = {(p.timestamp, p.metric) for p in anomaly_points}
        for metric in metric_cols:
            v = orig_df[metric].copy()
            for ts_idx in orig_df.index:
                if (str(ts_idx), metric) in anomaly_ts:
                    v.loc[ts_idx] = np.nan
            fitted = v.interpolate(method="linear", limit_direction="both")
            for ts_idx in orig_df.index:
                ts_str = str(ts_idx)
                fv = float(fitted.loc[ts_idx]); av = float(orig_df.loc[ts_idx, metric])
                if math.isfinite(fv) and math.isfinite(av):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str, metric=metric,
                        predicted=round(fv, 6), actual=round(av, 6),
                    ))
```

### B.11 Local forecast pipeline (sliding retrains)
```python
n = len(series)
min_train = max(forecast_model.min_train_series_length, 10)
train_start = max(int(n * 0.3), min_train + 1)
stride = max(1, n // 20)

all_pred_vals = np.full(n, np.nan)
i = train_start
while i < n:
    horizon = min(stride, n - i)
    try:
        m = build_forecast_model(config.model_id, config.params)
        m.fit(series[:i])
        pred = m.predict(horizon).to_dataframe().iloc[:, 0].values.astype(float)
        all_pred_vals[i : i + len(pred)] = pred
    except Exception as e:
        logger.warning("Forecast chunk failed at %d for %s: %s", i, metric, e)
    i += stride

# Build sub-series at first prediction index, fill any gap with actual to keep lengths aligned,
# then run the residual scorer.
```

### B.12 Global forecast pipeline (`historical_forecasts`)
```python
n = len(series)
if config.model_id in FOUNDATION_MODELS and n > MAX_FOUNDATION_POINTS:  # 3000
    step = -(-n // MAX_FOUNDATION_POINTS)  # ceil division
    series = series[::step]; n = len(series)

train_start = max(int(n * 0.3), min_train + 1)
model.fit(series[:train_start])

if is_foundation:
    fh = FOUNDATION_CHUNK_SIZE  # 128
    parts = model.historical_forecasts(series, start=train_start, forecast_horizon=fh,
                                       stride=fh, retrain=False, last_points_only=False, verbose=False)
    forecasts = parts[0]
    for p in parts[1:]:
        forecasts = forecasts.append(p)
else:
    forecasts = model.historical_forecasts(series, start=train_start, forecast_horizon=1,
                                           stride=1, retrain=False, last_points_only=True, verbose=False)
```

### B.13 Severity / merge / damping / volume gate (canonical bodies)
```python
def _classify_severity(score, threshold):
    if score > threshold * 2.0: return "high"
    if score > threshold * 1.5: return "medium"
    return "low"

def _merge_into_regions(points, max_gap=2):
    grouped = defaultdict(list)
    for p in points:
        dim_key = str(sorted(p.dimension_values.items())) if p.dimension_values else ""
        grouped[(p.metric, dim_key)].append(p)

    regions = []
    for (metric, _), group in grouped.items():
        group.sort(key=lambda p: p.timestamp)
        # median time step between consecutive group members
        diffs = [(pd.Timestamp(group[j].timestamp) - pd.Timestamp(group[j-1].timestamp)).total_seconds()
                 for j in range(1, len(group))]
        diffs = [d for d in diffs if d > 0]
        median_step = sorted(diffs)[len(diffs)//2] if diffs else 3600

        cur = [group[0]]
        for j in range(1, len(group)):
            gap = (pd.Timestamp(group[j].timestamp) - pd.Timestamp(cur[-1].timestamp)).total_seconds()
            if gap <= median_step * max_gap:
                cur.append(group[j])
            else:
                regions.append(_region_from_points(cur, metric))
                cur = [group[j]]
        regions.append(_region_from_points(cur, metric))
    return regions

def _apply_persistence_damping(regions, points, damping, min_points, threshold):
    survivors = [r for r in regions if r.point_count >= min_points]
    damped = []
    for r in survivors:
        if damping > 0 and r.point_count > 1:
            eff = r.avg_score * (1 + damping * math.log2(r.point_count))
            damped.append(AnomalyRegion(start=r.start, end=r.end, metric=r.metric,
                                        severity=_classify_severity(eff, threshold),
                                        avg_score=round(eff, 4), point_count=r.point_count,
                                        dimension_values=r.dimension_values))
        else:
            damped.append(r)
    if len(survivors) < len(regions):
        kept = []
        for p in points:
            for r in survivors:
                if (p.metric == r.metric and r.start <= p.timestamp <= r.end
                        and p.dimension_values == r.dimension_values):
                    kept.append(p); break
        points = kept
    return damped, points

def _apply_volume_gate(points, df, ts_col, vol_metric, threshold):
    if vol_metric not in df.columns:
        return points
    lookup = {str(row[ts_col]): float(row[vol_metric])
              for _, row in df[[ts_col, vol_metric]].iterrows() if pd.notna(row[vol_metric])}
    return [p for p in points if lookup.get(p.timestamp, 0.0) >= threshold]
```

### B.14 Statistical pipelines (canonical numeric core)

**Modified Z-Score**:
```python
median = np.median(values)
mad = np.median(np.abs(values - median)) or (np.std(values) or 1.0)
scores = 0.6745 * np.abs(values - median) / mad
is_anom = scores > zscore_threshold
```

**STL+GESD**:
```python
from statsmodels.tsa.seasonal import STL
result = STL(series, period=period, robust=True).fit()
residual, trend, seasonal = result.resid.values, result.trend.values, result.seasonal.values
mad = np.median(np.abs(residual - np.median(residual))) or (np.std(residual) or 1.0)
scores = np.abs(residual) / mad
max_outliers = max(1, int(max_anomaly_pct * len(residual)))
outlier_idxs = set(_gesd_test(residual, max_outliers))   # see _gesd_test below
fitted_values = trend + seasonal
```

**`_gesd_test`** (α=0.05):
```python
def _gesd_test(residuals, max_outliers, alpha=0.05):
    from scipy import stats as scipy_stats
    n = len(residuals)
    if n < 3 or max_outliers < 1: return []
    indices = list(range(n)); data = residuals.copy(); out = []
    for i in range(min(max_outliers, n - 2)):
        if len(data) < 3: break
        mean, std = np.mean(data), np.std(data, ddof=1)
        if std < 1e-12: break
        dev = np.abs(data - mean); j = int(np.argmax(dev))
        test_stat = dev[j] / std
        p = max(min(1.0 - alpha / (2.0 * (n - i)), 1.0 - 1e-12), 1e-12)
        t_crit = scipy_stats.t.ppf(p, n - i - 2)
        crit = ((n - i - 1) * t_crit) / math.sqrt((n - i - 2 + t_crit**2) * (n - i))
        if test_stat > crit:
            out.append(indices[j]); data = np.delete(data, j); del indices[j]
        else:
            break
    return out
```

**Spectral Residual**:
```python
def _spectral_residual_scores(values, spectral_window=3, score_window=21):
    n = len(values)
    if n < 3: return np.zeros(n)
    f = np.fft.fft(values)
    amp, ph = np.abs(f), np.angle(f)
    log_amp = np.log(amp + 1e-12)
    avg = np.convolve(log_amp, np.ones(spectral_window) / spectral_window, mode="same")
    sr = log_amp - avg
    sal = np.abs(np.fft.ifft(np.exp(sr + 1j * ph))) ** 2
    if score_window > 1:
        sal = np.convolve(sal, np.ones(score_window) / score_window, mode="same")
    return sal
```

**CUSUM** (two-sided):
```python
mu, sigma = np.mean(values), np.std(values, ddof=1) or 1.0
k, h = drift * sigma, threshold_h * sigma
s_pos = np.zeros(n); s_neg = np.zeros(n); scores = np.zeros(n)
for j in range(1, n):
    s_pos[j] = max(0.0, s_pos[j-1] + (values[j] - mu) - k)
    s_neg[j] = max(0.0, s_neg[j-1] - (values[j] - mu) - k)
    scores[j] = max(s_pos[j], s_neg[j])
is_anom = scores > h
```

**Hampel**:
```python
half = max(1, int(params.get("window", 11)) // 2)
n_sigma = float(params.get("n_sigma", 3.0))
for j in range(n):
    win = values[max(0, j-half):min(n, j+half+1)]
    med = np.median(win)
    mad = np.median(np.abs(win - med))
    sigma_est = 1.4826 * mad if mad > 1e-12 else 1e-12
    scores[j] = abs(values[j] - med) / sigma_est
is_anom = scores > n_sigma
```

**Change point (PELT, ruptures)**:
```python
import ruptures as rpt
algo = rpt.Pelt(model=cost_model, min_size=2, jump=1).fit(values)
cps = algo.predict(pen=penalty * np.log(n))
cp_set = set(cps[:-1]) if cps else set()
baseline = np.zeros(n); prev = 0
for bp in sorted(cp_set | {n}):
    baseline[prev:bp] = np.mean(values[prev:bp]); prev = bp
gstd = np.std(values, ddof=1) or 1.0
scores = np.abs(values - baseline) / gstd
for cp in sorted(cp_set):
    for off in range(-2, 3):
        j = cp + off
        if 0 <= j < n:
            l = np.mean(values[max(0, cp-6):cp]); r = np.mean(values[cp:min(n, cp+6)])
            scores[j] = max(scores[j], abs(r - l) / gstd)
```

### B.15 Peer pipeline core patterns

Every peer pipeline shares this shape:

```python
def _prepare_peer_groups(df, ts_col, dim_col, metric_cols, min_peers):
    # 1. Build dict[group_name -> aligned_array(T x M)] using union of timestamps
    # 2. Linearly interpolate intra-group gaps; track mask of original (non-interpolated) timestamps
    # 3. Reject if len(groups) < max(min_peers, 3)
    return aligned, group_names, masks, time_index   # arrays per group

# Score consensus & emit anomalies per metric using a global per-metric quantile threshold
def _emit_peer_scores_and_anomalies(score_matrix, masks, metric_cols, time_index,
                                    config, anomaly_points, all_scores):
    for m_idx, metric in enumerate(metric_cols):
        all_pos = []
        for g in group_names:
            mask = masks[g]
            s = score_matrix[g][:, m_idx]; s = s[mask]
            all_pos.extend(s[s > 0])
        thr = float(np.quantile(all_pos, min(config.detector_threshold, 0.999))) if all_pos else 1.0
        for g in group_names:
            mask = masks[g]; vals = score_matrix[g][:, m_idx]
            for t_idx, t in enumerate(time_index):
                if not mask[t_idx]: continue
                score = float(vals[t_idx])
                ts_str = str(t)
                all_scores.append({"timestamp": ts_str, "metric": metric, "score": round(score, 6)})
                if score >= thr:
                    anomaly_points.append(DartsAnomalyPoint(
                        timestamp=ts_str, metric=metric, value=0.0,
                        score=round(score, 6), is_anomaly=True,
                        severity=_classify_severity(score, thr),
                        dimension_values={dim_col: g},
                    ))
```

**Peer Divergence** (per metric):
```python
stacked = np.stack([aligned[g] for g in group_names], axis=-1)   # (T, M, P)
consensus = np.nanmean(stacked, axis=-1) if method == "mean" else np.nanmedian(stacked, axis=-1)
deviation = np.abs(stacked - consensus[..., None])               # (T, M, P)

if normalization == "pct":
    eps = (np.nanmax(np.abs(consensus)) or 1.0) * 1e-6
    safe = np.where(np.abs(consensus) > eps, np.abs(consensus), eps)
    norm = (deviation / safe[..., None]) * 100.0
elif normalization == "zscore":
    std = np.nanstd(stacked, axis=-1)
    safe = np.where(std > 0, std, 1.0)
    norm = deviation / safe[..., None]
else:  # mad
    mad = np.nanmedian(deviation, axis=-1)
    safe = np.where(mad > 0, mad, 1.0)
    norm = deviation / safe[..., None]

# norm is (T, M, P); reshape to per-group score_matrix[g][:, m]
```

**Peer PCA**:
```python
from sklearn.decomposition import PCA as SkPCA
from sklearn.preprocessing import StandardScaler
for m_idx, metric in enumerate(metric_cols):
    X = np.array([aligned[g][:, m_idx] for g in group_names])           # (N, T)
    Xs = StandardScaler().fit_transform(X)
    n_comp = min(max(1, int(n_components * min(Xs.shape))), min(Xs.shape) - 1)
    pca = SkPCA(n_components=n_comp).fit(Xs)
    Xr = pca.inverse_transform(pca.transform(Xs))
    err = np.abs(Xs - Xr)
    for i, g in enumerate(group_names):
        score_matrix[g][:, m_idx] = err[i]
```

**Peer Functional Depth** (Modified Band Depth + envelope):
```python
curves = np.array([aligned[g][:, m_idx] for g in group_names])     # (N, T)
median = np.nanmedian(curves, axis=0)
q25, q75 = np.nanpercentile(curves, [25, 75], axis=0)
iqr = np.where(q75 - q25 > 0, q75 - q25, 1.0)
env = np.abs(curves - median) / iqr                                # (N, T)

mbd = np.zeros(N)
for i in range(N):
    s, c = 0.0, 0
    for j in range(N):
        if j == i: continue
        for k in range(j+1, N):
            if k == i: continue
            lo = np.minimum(curves[j], curves[k]); hi = np.maximum(curves[j], curves[k])
            s += np.sum((curves[i] >= lo) & (curves[i] <= hi)) / T; c += 1
    mbd[i] = s / c if c else 0.0
for i, g in enumerate(group_names):
    weight = 1.0 + (1.0 - mbd[i])  # range [1, 2]
    score_matrix[g][:, m_idx] = env[i] * weight
```

**Peer Feature Isolation** (`_extract_ts_features` returns ~17-D vector):
```python
def _extract_ts_features(s):
    from scipy import stats as sp
    f = []
    f += [np.nanmean(s), np.nanstd(s),
          float(sp.skew(s, nan_policy='omit')), float(sp.kurtosis(s, nan_policy='omit')),
          np.nanmedian(s)]
    q25, q75 = np.nanpercentile(s, [25, 75])
    f += [q75 - q25, np.nanmax(s) - np.nanmin(s)]
    diff = np.diff(s)
    f += [np.nanstd(diff), np.nanmean(np.abs(diff))]
    cs = s - np.nanmean(s); var = np.nanvar(s)
    for lag in (1, 5, 10):
        f.append(float(np.nanmean(cs[:-lag] * cs[lag:]) / var) if lag < len(s) and var > 0 else 0.0)
    x = np.arange(len(s), dtype=float); v = np.isfinite(s)
    f.append(float(sp.linregress(x[v], s[v]).slope) if v.sum() > 2 else 0.0)
    mc = s - np.nanmean(s); f.append(np.sum(np.diff(np.sign(mc)) != 0) / max(len(s)-1, 1))
    try:
        p = np.abs(np.fft.rfft(s - np.nanmean(s))) ** 2
        pn = (p / (p.sum() + 1e-12)); pn = pn[pn > 0]
        f.append(float(-np.sum(pn * np.log2(pn + 1e-12))))
    except Exception:
        f.append(0.0)
    return np.array(f, dtype=float)

# Run IF over feature matrix → node weights → combine with envelope distance
clf = IForest(contamination=min(contam, (N-1)/N), random_state=42).fit(feat)
node_scores = clf.decision_scores_
nw = (node_scores - node_scores.min()) / max(node_scores.max() - node_scores.min(), 1e-12)
score_matrix[g][:, m_idx] = envelope_dist[i] * (1.0 + nw[i] * 2.0)
```

**Peer DTW + LOF**:
```python
from dtaidistance import dtw
from sklearn.neighbors import LocalOutlierFactor
D = np.zeros((N, N))
for i in range(N):
    for j in range(i+1, N):
        d = dtw.distance(series_list[i], series_list[j], window=dtw_window, use_pruning=True)
        D[i, j] = D[j, i] = d
lof = LocalOutlierFactor(n_neighbors=min(lof_neighbors, N-1), metric="precomputed", contamination="auto")
lof.fit(D)
node_scores = -lof.negative_outlier_factor_  # higher = more anomalous
# combine with envelope distance as in feature isolation
```

**Peer Matrix Profile (STUMPY)**:
```python
import stumpy
m = max(4, min(int(params.get("subsequence_length", 24)), T // 2))
consensus_m = np.nanmedian(np.stack([aligned[g][:, m_idx] for g in group_names], axis=-1), axis=-1)

for g in group_names:
    node = aligned[g][:, m_idx].astype(np.float64)
    mp = stumpy.stump(node, m=m, T_B=consensus_m.astype(np.float64))
    vals = mp[:, 0].astype(float)
    padded = np.zeros(T)
    off = (m - 1) // 2
    padded[off:off + len(vals)] = vals
    if off > 0:                         padded[:off] = vals[0]
    if T - off - len(vals) > 0:         padded[off + len(vals):] = vals[-1]
    score_matrix[g][:, m_idx] = padded
```

### B.16 Foundation-model adapters (caching/shapes)

**TSPulse** (lazy-load, cache by num_channels):
```python
from tsfm_public.models.tspulse.modeling_tspulse import TSPulseForReconstruction
from tsfm_public.toolkit.time_series_anomaly_detection_pipeline import TimeSeriesAnomalyDetectionPipeline
_tspulse_cache = {}

def _get_tspulse(num_channels):
    if num_channels not in _tspulse_cache:
        _tspulse_cache[num_channels] = TSPulseForReconstruction.from_pretrained(
            "ibm-granite/granite-timeseries-tspulse-r1",
            num_input_channels=num_channels, revision="main", mask_type="user",
        )
    return _tspulse_cache[num_channels]

mode = {"time+fft": ["time", "fft"], "time": ["time"], "fft": ["fft"]}[
    str(config.params.get("scoring_mode", "time+fft"))]

pipeline = TimeSeriesAnomalyDetectionPipeline(
    _get_tspulse(len(metric_cols)),
    timestamp_column=ts_col, target_columns=metric_cols, prediction_mode=mode,
    aggregation_length=int(config.params.get("aggregation_length", 64)),
    aggr_function="max",
    smoothing_length=int(config.params.get("smoothing_length", 8)),
    least_significant_scale=0.01, least_significant_score=0.1,
)
result_df = pipeline(tsp_df, batch_size=256)
# result_df["anomaly_score"]
```

**MOMENT** (lazy-load + per-device cache):
```python
from momentfm import MOMENTPipeline
import torch
_moment_cache = {}
key = f"{model_variant}|{device_str}"
if key not in _moment_cache:
    pipe = MOMENTPipeline.from_pretrained(model_variant,
        model_kwargs={"task_name": "reconstruction"})
    pipe.init()
    pipe = pipe.to(torch.device(device_str))
    _moment_cache[key] = pipe
pipe = _moment_cache[key]

# Per-metric: window into context_length, normalize, reconstruct, score = (x - x_hat)^2
```

**Lag-Llama**:
```python
from huggingface_hub import hf_hub_download
from lag_llama.gluon.estimator import LagLlamaEstimator
from gluonts.dataset.pandas import PandasDataset

ckpt = hf_hub_download(repo_id="time-series-foundation-models/Lag-Llama", filename="lag-llama.ckpt")
estimator = LagLlamaEstimator(
    ckpt_path=ckpt,
    prediction_length=prediction_length,
    context_length=context_length,
    input_size=1, n_layer=8, n_embd_per_head=32, n_head=4,
    num_samples=num_samples, device=torch.device(device_str),
)
predictor = estimator.create_predictor(batch_size=64)
forecasts = list(predictor.predict(PandasDataset(dict(enumerate(entries)), freq=freq)))
# anomaly score per future point: |actual − median(samples)| / std(samples)
```

---

# Appendix C — Frontend Behavior Reference (concrete code)

### C.1 `composables/useWebSocket.ts`
```ts
export function useWebSocket(sessionId: string) {
  const connected = ref(false)
  const lastMessage = ref<WebSocketMessage | null>(null)
  const handlers = new Map<string, ((m: WebSocketMessage) => void)[]>()

  let socket: WebSocket | null = null
  let reconnectDelay = 1000   // exponential, max 16000
  let manuallyClosed = false

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/api/ws/${sessionId}`
    socket = new WebSocket(url)
    socket.onopen = () => { connected.value = true; reconnectDelay = 1000 }
    socket.onmessage = (e) => {
      try {
        const msg: WebSocketMessage = JSON.parse(e.data)
        if (msg.type === 'ping') return
        lastMessage.value = msg
        handlers.get(msg.type)?.forEach((h) => h(msg))
        handlers.get('*')?.forEach((h) => h(msg))
      } catch { /* ignore */ }
    }
    socket.onclose = () => {
      connected.value = false
      if (manuallyClosed) return
      setTimeout(connect, reconnectDelay)
      reconnectDelay = Math.min(reconnectDelay * 2, 16000)
    }
  }

  function on(type: string, handler: (m: WebSocketMessage) => void) {
    const list = handlers.get(type) ?? []
    list.push(handler)
    handlers.set(type, list)
  }

  function disconnect() { manuallyClosed = true; socket?.close() }

  onMounted(connect)
  onBeforeUnmount(disconnect)
  return { connected, lastMessage, on, disconnect }
}
```

### C.2 `stores/upload.ts` chunked upload loop
```ts
async function upload(file: File) {
  filename.value = file.name; fileSize.value = file.size; status.value = 'uploading'
  const isParquet = file.name.toLowerCase().endsWith('.parquet')
  const init = await initUpload({
    filename: file.name, file_size: file.size, chunk_size: CHUNK_SIZE,
    file_type: isParquet ? 'parquet' : 'csv',
  })
  sessionId.value = init.session_id
  uploadId.value  = init.upload_id
  totalChunks.value = init.total_chunks

  for (let i = 0; i < init.total_chunks; i++) {
    const start = i * CHUNK_SIZE
    const end   = Math.min(start + CHUNK_SIZE, file.size)
    const blob  = file.slice(start, end)
    await uploadChunk(init.session_id, i, blob)   // sequential
    chunksUploaded.value = i + 1
  }
  await completeUpload(init.session_id)
  status.value = 'parsing'   // WS or polling will set 'ready'
}
```

### C.3 `stores/models.ts` — exact computeds
```ts
const thresholdScore = computed(() => {
  if (!results.value || !results.value.scores.length) return null
  const scores = results.value.scores.map((s) => s.score).filter((v) => v > 0)
  if (!scores.length) return null

  if (detectorType.value === 'threshold') return detectorThreshold.value
  if (detectorType.value === 'iqr') {
    scores.sort((a, b) => a - b)
    const q1 = scores[Math.floor(scores.length * 0.25)]
    const q3 = scores[Math.floor(scores.length * 0.75)]
    return q3 + detectorThreshold.value * (q3 - q1)
  }
  scores.sort((a, b) => a - b)
  const idx = Math.min(Math.floor(detectorThreshold.value * scores.length), scores.length - 1)
  return scores[idx]
})

function classifySeverity(score: number, t: number): 'low'|'medium'|'high' {
  if (score > t * 2.0) return 'high'
  if (score > t * 1.5) return 'medium'
  return 'low'
}

const effectiveAnomalies = computed<DartsAnomalyPoint[]>(() => {
  const t = thresholdScore.value
  if (!results.value || t == null) return []
  return results.value.scores
    .filter((s) => s.score >= t)
    .map((s) => ({
      timestamp: s.timestamp, metric: s.metric, value: 0, score: s.score,
      is_anomaly: true, severity: classifySeverity(s.score, t),
    }))
})

const effectiveRegions = computed<AnomalyRegion[]>(() => {
  if (!results.value) return []
  const t = thresholdScore.value ?? 1.0
  // Group anomalies by metric
  const byMetric: Record<string, DartsAnomalyPoint[]> = {}
  for (const p of effectiveAnomalies.value) (byMetric[p.metric] ??= []).push(p)

  const regs: AnomalyRegion[] = []
  for (const [metric, pts] of Object.entries(byMetric)) {
    pts.sort((a, b) => a.timestamp.localeCompare(b.timestamp))
    // median time step (ms); default 1h
    const diffs: number[] = []
    for (let i = 1; i < pts.length; i++) {
      const d = new Date(pts[i].timestamp).getTime() - new Date(pts[i-1].timestamp).getTime()
      if (d > 0) diffs.push(d)
    }
    diffs.sort((a, b) => a - b)
    const medianStep = diffs.length ? diffs[Math.floor(diffs.length / 2)] : 3600000

    let cur: DartsAnomalyPoint[] = [pts[0]]
    const flush = () => {
      const start = cur[0].timestamp, end = cur[cur.length - 1].timestamp
      const avg = cur.reduce((s, p) => s + p.score, 0) / cur.length
      let sev = cur.reduce((m, p) => Math.max(m, p.severity === 'high' ? 3 : p.severity === 'medium' ? 2 : 1), 0)
      let avgFinal = avg
      if (persistenceDamping.value > 0 && cur.length > 1) {
        avgFinal = avg * (1 + persistenceDamping.value * Math.log2(cur.length))
        sev = Math.max(sev, classifySeverity(avgFinal, t) === 'high' ? 3 :
                            classifySeverity(avgFinal, t) === 'medium' ? 2 : 1)
      }
      regs.push({
        start, end, metric,
        severity: sev === 3 ? 'high' : sev === 2 ? 'medium' : 'low',
        avg_score: Number(avgFinal.toFixed(4)),
        point_count: cur.length, dimension_values: null,
      })
    }
    for (let i = 1; i < pts.length; i++) {
      const gap = new Date(pts[i].timestamp).getTime() - new Date(pts[i-1].timestamp).getTime()
      if (gap <= medianStep * 2) cur.push(pts[i])
      else { flush(); cur = [pts[i]] }
    }
    flush()
  }
  return regs.filter((r) => r.point_count >= minAnomalyPoints.value)
})

const effectiveSummary = computed(() => {
  if (!results.value) return null
  const points = effectiveAnomalies.value
  const bySev: Record<string, number> = { low: 0, medium: 0, high: 0 }
  const byMet: Record<string, number> = {}
  for (const p of points) {
    bySev[p.severity] = (bySev[p.severity] ?? 0) + 1
    byMet[p.metric]   = (byMet[p.metric]   ?? 0) + 1
  }
  return {
    total_points_analyzed: results.value.summary.total_points_analyzed,
    total_anomalies:       points.length,
    total_regions:         effectiveRegions.value.length,
    by_severity: bySev,
    by_metric:   byMet,
  }
})

// regionExplanations: Map<`${metric}|${start}|${end}`, string>
//   built by calling explainRegion(region, analysis.chartData.series) for each region.
```

### C.4 DimensionFilter — glob → regex
```ts
function globToRegex(pattern: string): RegExp {
  const escaped = pattern.replace(/([.+?^${}()|[\]\\])/g, '\\$1')
  return new RegExp(`^${escaped.replace(/\*/g, '.*')}$`, 'i')   // case-insensitive
}

let timers: Record<string, ReturnType<typeof setTimeout>> = {}
function onPatternInput(column: string) {
  if (timers[column]) clearTimeout(timers[column])
  timers[column] = setTimeout(() => {
    const raw = (patternText.value[column] || '').trim()
    if (!raw) { emit('update-filter', column, []); return }
    const patterns = raw.split(',').map((p) => p.trim()).filter(Boolean)
    const regexes = patterns.map(globToRegex)
    const matched = dim.values.filter((v) => regexes.some((re) => re.test(v)))
    emit('update-filter', column, matched)
  }, 400)   // debounce
}
```
Match counter: `(props.filters[column] ?? []).length` (rendered as e.g. "5 matched").

### C.5 KPIEditor — autocomplete logic
```ts
function getTokenAtCursor() {
  const pos = el.selectionStart ?? newFormula.value.length
  const txt = newFormula.value
  let start = pos
  while (start > 0 && /[A-Za-z0-9_.]/.test(txt[start - 1])) start--
  if (start > 0 && txt[start - 1] === '`') start--
  let end = pos
  while (end < txt.length && /[A-Za-z0-9_.]/.test(txt[end])) end++
  if (end < txt.length && txt[end] === '`') end++
  const token = txt.slice(start, end).replace(/`/g, '')
  return token ? { token, start, end } : null
}

function updateSuggestions() {
  const r = getTokenAtCursor()
  if (!r || r.token.length < 1) { showSuggestions.value = false; return }
  const q = r.token.toLowerCase()
  const filtered = props.availableColumns.filter((c) => c.toLowerCase().includes(q))
  suggestions.value = filtered.slice(0, 50)
  highlightIndex.value = filtered.length ? 0 : -1
  showSuggestions.value = filtered.length > 0
}

function onKeydown(e: KeyboardEvent) {
  if (!showSuggestions.value || !suggestions.value.length) return
  if (e.key === 'ArrowDown') { e.preventDefault();
    highlightIndex.value = Math.min(highlightIndex.value + 1, suggestions.value.length - 1) }
  else if (e.key === 'ArrowUp') { e.preventDefault();
    highlightIndex.value = Math.max(highlightIndex.value - 1, 0) }
  else if (e.key === 'Enter' || e.key === 'Tab') {
    if (highlightIndex.value >= 0) { e.preventDefault(); applySuggestion(suggestions.value[highlightIndex.value]) }
  } else if (e.key === 'Escape') { showSuggestions.value = false }
}

function applySuggestion(col: string) {
  const r = getTokenAtCursor()
  const wrap = `\`${col}\``
  newFormula.value = r ? newFormula.value.slice(0, r.start) + wrap + newFormula.value.slice(r.end)
                       : newFormula.value + wrap
  showSuggestions.value = false
}
```

Validation pipeline before save: name non-empty + unique vs metrics + KPIs + `validateKPIFormula(sessionId, formula)` server roundtrip.

### C.6 AppHeader — step inference, theme, clear
```ts
const route = useRoute()
const currentStep = computed(() => {
  return ({ upload: 1, preview: 2, configure: 3, models: 4, analysis: 5 } as const)[
    route.name as 'upload'|'preview'|'configure'|'models'|'analysis'
  ] ?? 1
})

// Theme stored in localStorage (persists across sessions)
const theme = ref(localStorage.getItem('theme') ?? 'dark')
function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('theme', theme.value)
}

async function clearAll() {
  const sid = sessionId.value
  if (sid) {
    try { await deleteSession(sid) } catch { /* may already be gone */ }
    sessionStorage.removeItem(`dataset-selections:${sid}`)
    sessionStorage.removeItem(`model-selection:${sid}`)
  }
  useUploadStore().reset(); useDatasetStore().reset()
  useModelsStore().reset(); useAnalysisStore().reset()
  router.push({ name: 'upload' })
}

function downloadParquet() {
  if (!sessionId.value) return
  window.open(`/api/datasets/${sessionId.value}/download`, '_blank')
}
```

Step CSS state: `'nav-step--completed': step.number < currentStep`, `'nav-step--active': step.number === currentStep`, `'nav-step--disabled': step.number > currentStep`. Future steps are not clickable; past steps push to that step's route.

### C.7 ParamPanel — detector slider configs (precise)

| detectorType | input | min | max | step | format |
|---|---|---|---|---|---|
| `quantile`  | range slider | 0.5 | 0.999 | 0.005 | shown as percentile, e.g. `0.95 → "Top 5% flagged"` |
| `iqr`       | range slider | 0.5 | 5.0   | 0.1   | shown as `Q3 + {threshold}×IQR` |
| `threshold` | number input | 0   | —     | 0.1   | raw numeric value |

Score-stats helpers:
```ts
const scoreStats = computed(() => {
  if (!props.results || !props.results.scores.length) return null
  const v = props.results.scores.map((s) => s.score).filter((x) => x > 0).sort((a, b) => a - b)
  if (!v.length) return null
  const pct = (p: number) => v[Math.min(Math.floor(p * v.length), v.length - 1)]
  return { min: v[0], p50: pct(0.5), p90: pct(0.9), p95: pct(0.95), p99: pct(0.99), max: v[v.length-1] }
})
```
Quick-set buttons: p50 / p90 / p95 / p99 / max — active state `Math.abs(detectorThreshold - val) < 0.001`.

Reset defaults:
```ts
function resetDefaults() {
  const d: Record<string, number|boolean|string> = {}
  for (const p of props.model.params) d[p.name] = p.default
  emit('update:params', d)
}
```

Accordion state initial: `{ preprocessing: false, transforms: false, filtering: false }`.

### C.8 AnomalyTable sort comparator
```ts
const severityOrder = { high: 3, medium: 2, low: 1 } as const

function sortFn(a: AnomalyRegion, b: AnomalyRegion): number {
  let cmp = 0
  switch (sortField.value) {
    case 'start':    cmp = a.start.localeCompare(b.start); break
    case 'severity': cmp = severityOrder[a.severity] - severityOrder[b.severity]; break
    case 'metric':   cmp = a.metric.localeCompare(b.metric); break
    case 'score':    cmp = a.avg_score - b.avg_score; break
  }
  return sortAsc.value ? cmp : -cmp
}
```
Expand state: `Set<number>` keyed by row index. Chevron button uses `@click.stop="toggleRow(i)"` to prevent row-level `region-click` emit.

### C.9 AnalysisView — zoom save/restore + debounce + WS
```ts
let savedZoom: { start: number; end: number } | null = null
function handleRun() {
  savedZoom = chartRef.value?.getZoomRange() ?? null
  models.runDetection(props.sessionId)
}
watch(() => models.results, (nv) => {
  if (nv && savedZoom) {
    const z = savedZoom; savedZoom = null
    requestAnimationFrame(() => chartRef.value?.restoreZoom(z))
  }
})

// Transform/smoothing/infill changes reload chart (debounced 300 ms)
let timer: ReturnType<typeof setTimeout> | null = null
watch([() => models.transforms, () => models.smoothingWindow, () => models.infill], () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(async () => {
    await reloadChartData()
    if (!lockZoom.value) chartKey.value++   // force chart remount
  }, 300)
}, { deep: true })

// WebSocket handlers
const { on } = useWebSocket(props.sessionId)
on('progress', (m) => { if (m.stage === 'analysis') models.setProgress(m.detail ?? '', m.progress ?? 0) })
on('complete', (m) => {
  if (m.stage === 'analysis' && m.run_id) {
    models.setComplete(m.run_id)
    models.loadResults(props.sessionId, m.run_id)
  }
})
on('error', (m) => { models.error = m.detail ?? 'Analysis failed'; models.isRunning = false })
```

### C.10 UploadView — polling fallback
```ts
let pollTimer: ReturnType<typeof setInterval> | null = null
function startPolling(sessionId: string) {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const s = await getUploadStatus(sessionId)
      if (s.status === 'ready')      { upload.setReady(); stopPolling() }
      else if (s.status === 'error') { upload.setError(s.error ?? 'Parsing failed'); stopPolling() }
      else                            { upload.setParsingProgress(s.parsing_progress) }
    } catch { /* swallow */ }
  }, 2000)
}
function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

watch(() => upload.status, (status) => {
  if (status === 'ready' && upload.sessionId) {
    stopPolling()
    router.push({ name: 'preview', params: { sessionId: upload.sessionId } })
  }
})
```

### C.11 `utils/explainer.ts` — pattern classification thresholds
```ts
type PatternType =
  | 'single_outlier' | 'spike_up' | 'spike_down' | 'volatility_increase'
  | 'gradual_drift_up' | 'gradual_drift_down'
  | 'level_shift_up' | 'level_shift_down' | 'sustained_deviation'

let pattern: PatternType
if (region.point_count === 1) {
  pattern = 'single_outlier'
} else if (region.point_count <= 3 && hasBaseline) {
  pattern = insideMean > beforeMean ? 'spike_up' : 'spike_down'
} else if (hasBaseline && beforeStd > 1e-10 && insideStd / beforeStd > 2.0) {
  pattern = 'volatility_increase'
} else if (region.point_count >= 4) {
  const corr = rankCorrelation(inside)   // Spearman
  if      (corr >  0.7) pattern = 'gradual_drift_up'
  else if (corr < -0.7) pattern = 'gradual_drift_down'
  else if (hasBaseline && insideMean > beforeMean) pattern = 'level_shift_up'
  else if (hasBaseline && insideMean < beforeMean) pattern = 'level_shift_down'
  else pattern = 'sustained_deviation'
} else {
  pattern = 'sustained_deviation'
}
```
Sentence templates (one per pattern):

| pattern | template |
|---|---|
| `single_outlier` | `{metric} had a single anomalous reading of {val} at {start}. {pctPhrase} the baseline of {baseline}.` |
| `spike_up` | `{metric} spiked to {max} around {start}, {pctPhrase} the preceding baseline of {baseline}.` |
| `spike_down` | `{metric} dropped sharply to {min} around {start}, {pctPhrase} the preceding baseline of {baseline}.` |
| `volatility_increase` | `{metric} became unusually volatile over {duration} starting {start}, with {ratio}x the normal variation.` |
| `gradual_drift_up` / `gradual_drift_down` | `{metric} gradually [increased/decreased] over {duration} starting {start}, [rising/falling] from {first} to {last}.` |
| `level_shift_up` / `level_shift_down` | `{metric} shifted to a [higher/lower] level averaging {mean} over {duration} starting {start}, [up/down] {pct}% from the prior baseline of {baseline}.` |
| `sustained_deviation` | `{metric} deviated from normal over {duration} starting {start}, averaging {mean} vs a baseline of {baseline} ({pctPhrase}).` |

`rankCorrelation` is plain Spearman: rank both `xs = [0..n-1]` and `ys = inside`, then compute Pearson correlation of the ranks.

---

# Appendix D — ResultsChart ECharts Option (concrete)

### D.1 Imports & module registration
```ts
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, ScatterChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent,
  DataZoomComponent, MarkAreaComponent, MarkLineComponent, ToolboxComponent,
} from 'echarts/components'

use([CanvasRenderer, LineChart, ScatterChart,
     GridComponent, TooltipComponent, LegendComponent,
     DataZoomComponent, MarkAreaComponent, MarkLineComponent, ToolboxComponent])
```

### D.2 Theme reactivity
```ts
const themeVersion = ref(0)
const obs = new MutationObserver(() => themeVersion.value++)
obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
onBeforeUnmount(() => obs.disconnect())

function themeColors() {
  const dark = (document.documentElement.dataset.theme ?? 'dark') !== 'light'
  return dark
    ? { axisLabel:'#64748b', axisLine:'#334155', splitLine:'#1e293b',
        tooltipBg:'rgba(15,23,42,0.95)', tooltipBorder:'rgba(99,102,241,0.3)', tooltipText:'#e2e8f0',
        legend:'#94a3b8', toolboxIcon:'#64748b',
        dataZoomBg:'#0f172a', dataZoomBorder:'#334155',
        dataZoomFiller:'rgba(99,102,241,0.15)', dataZoomText:'#64748b' }
    : { axisLabel:'#6b7280', axisLine:'#d1d5db', splitLine:'#e5e7eb',
        tooltipBg:'rgba(255,255,255,0.95)', tooltipBorder:'rgba(99,102,241,0.2)', tooltipText:'#1f2937',
        legend:'#4b5563', toolboxIcon:'#6b7280',
        dataZoomBg:'#f9fafb', dataZoomBorder:'#d1d5db',
        dataZoomFiller:'rgba(99,102,241,0.12)', dataZoomText:'#6b7280' }
}
```

### D.3 Option object skeleton
```ts
const SCORE_PALETTE = ['#f97316','#ef4444','#eab308','#f472b6','#fb923c']
const SCORER_IDS = new Set(['kmeans','isolation_forest','lof','ecod','wasserstein'])

const chartOption = computed(() => {
  if (!props.chartData || !props.chartData.series.length) return {}
  const tc = themeColors()
  const hasScores = !!(props.results && props.results.scores.length)
  const fitLabel =
    props.results?.config.model_id === 'peer_divergence' ? 'Consensus'
    : SCORER_IDS.has(props.results?.config.model_id ?? '') ? 'Fitted'
    : 'Forecast'

  // 1) Compute global timeMin/timeMax across all series for both grids' axes
  let timeMin = Infinity, timeMax = -Infinity
  for (const s of props.chartData.series) {
    if (!s.timestamps.length) continue
    timeMin = Math.min(timeMin, new Date(s.timestamps[0]).getTime())
    timeMax = Math.max(timeMax, new Date(s.timestamps[s.timestamps.length-1]).getTime())
  }

  // 2) Build mark areas (regions) — apply only to main grid
  const markAreaData: any[][] = []
  for (const r of (props.regions ?? [])) {
    markAreaData.push([
      { xAxis: r.start, itemStyle: { color: getSeverityBgColor(r.severity) } },
      { xAxis: r.end },
    ])
  }

  // 3) Main metric series + (optional) original-overlay series
  const seriesList: any[] = []
  props.chartData.series.forEach((s, i) => {
    const data = s.timestamps.map((t, k) => [t, s.values[k]])
    seriesList.push({
      name: s.name, type: 'line',
      xAxisIndex: 0, yAxisIndex: 0, data, symbol: 'none',
      lineStyle: { width: 1.5, color: getSeriesColor(i) },
      itemStyle: { color: getSeriesColor(i) },
      markArea: markAreaData.length ? { silent: true, data: markAreaData } : undefined,
    })
  })
  if (props.chartData.original_series) {
    props.chartData.original_series.forEach((s, i) => {
      const data = s.timestamps.map((t, k) => [t, s.values[k]])
      seriesList.push({
        name: s.name, type: 'line', xAxisIndex: 0, yAxisIndex: 0, data, symbol: 'none',
        lineStyle: { width: 1, type: 'dashed', color: getSeriesColor(i), opacity: 0.35 },
        itemStyle:  { color: getSeriesColor(i), opacity: 0.35 },
      })
    })
  }

  // 4) Forecast / fit overlay series (grouped per metric in props.results.forecast)
  if (props.showFitLine && props.results?.forecast) {
    const byMetric: Record<string, ForecastPoint[]> = {}
    for (const f of props.results.forecast) (byMetric[f.metric] ??= []).push(f)
    Object.keys(byMetric).forEach((m, fcIdx) => {
      const pts = byMetric[m]
      seriesList.push({
        name: `${fitLabel}: ${m}`, type: 'line',
        xAxisIndex: 0, yAxisIndex: 0,
        data: pts.map((p) => [p.timestamp, p.predicted]),
        symbol: 'none',
        lineStyle: { width: 1.5, type: 'dashed', color: getSeriesColor(props.chartData!.series.length + fcIdx) },
        itemStyle: { color: getSeriesColor(props.chartData!.series.length + fcIdx) },
      })
    })
  }

  // 5) Anomaly scatter (severity-colored). Resolve y-value from a metric series.
  const scatter = (props.anomalies ?? []).map((a) => {
    let y = a.value
    const s = props.chartData!.series.find((x) => x.name.endsWith(a.metric))
    if (s) {
      const idx = s.timestamps.indexOf(a.timestamp)
      if (idx >= 0 && s.values[idx] != null) y = s.values[idx] as number
    }
    return { value: [a.timestamp, y], itemStyle: { color: getSeverityColor(a.severity) } }
  })
  if (scatter.length) {
    seriesList.push({
      name: 'Anomalies', type: 'scatter', xAxisIndex: 0, yAxisIndex: 0,
      data: scatter, symbolSize: 6, z: 10, animation: false,
    })
  }

  // 6) Score line(s) (only if hasScores) — group scores by metric
  if (hasScores) {
    const byMetric: Record<string, [string, number][]> = {}
    for (const s of props.results!.scores) (byMetric[s.metric] ??= []).push([s.timestamp, s.score])
    const metrics = Object.keys(byMetric)
    metrics.forEach((m, i) => {
      const color = SCORE_PALETTE[i % SCORE_PALETTE.length]
      seriesList.push({
        name: metrics.length === 1 ? 'Anomaly Score' : `Score: ${m}`,
        type: 'line', xAxisIndex: 1, yAxisIndex: 1,
        data: byMetric[m], symbol: 'none',
        lineStyle: { width: 1, color }, itemStyle: { color },
        areaStyle: { color: color + '14' },   // 8% alpha
        markLine: (i === 0 && props.thresholdValue != null)
          ? { silent: true, symbol: 'none',
              lineStyle: { color: '#ef4444', type: 'dashed', width: 1 },
              data: [{ yAxis: props.thresholdValue }],
              label: { formatter: 'threshold: {c}', fontSize: 9, color: '#ef4444', position: 'insideEndTop' } }
          : undefined,
      })
    })
  }

  // 7) Apply emphasis/blur uniformly
  const series = seriesList.map((s) => ({
    ...s, emphasis: { focus: 'series' },
    blur: { lineStyle: { opacity: 0.15 }, itemStyle: { opacity: 0.15 }, areaStyle: { opacity: 0.05 } },
  }))

  return {
    backgroundColor: 'transparent', animation: true, animationDuration: 300,
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' },
               backgroundColor: tc.tooltipBg, borderColor: tc.tooltipBorder,
               textStyle: { color: tc.tooltipText, fontSize: 12 } },
    toolbox: { feature: { dataZoom: { yAxisIndex: 'none',
                                      title: { zoom: 'Drag to zoom', back: 'Undo zoom' } } },
               right: 24, top: 2, iconStyle: { borderColor: tc.toolboxIcon },
               emphasis: { iconStyle: { borderColor: '#6366f1' } } },
    legend: { textStyle: { color: tc.legend, fontSize: 11 }, top: 4, right: 80, type: 'scroll' },
    grid: [
      { left: 60, right: 20, top: 40, bottom: hasScores ? '42%' : 60 },
      ...(hasScores ? [{ left: 60, right: 20, top: '65%', bottom: 40 }] : []),
    ],
    xAxis: [
      { type: 'time', gridIndex: 0, min: timeMin, max: timeMax,
        axisLabel: { color: tc.axisLabel, fontSize: 10 },
        axisLine:  { lineStyle: { color: tc.axisLine } },
        splitLine: { show: false } },
      ...(hasScores ? [{ type: 'time', gridIndex: 1, min: timeMin, max: timeMax,
        axisLabel: { color: tc.axisLabel, fontSize: 10 },
        axisLine:  { lineStyle: { color: tc.axisLine } },
        splitLine: { show: false } }] : []),
    ],
    yAxis: [
      { type: 'value', gridIndex: 0,
        axisLabel: { color: tc.axisLabel, fontSize: 10 },
        splitLine: { lineStyle: { color: tc.splitLine } } },
      ...(hasScores ? [{ type: 'value', gridIndex: 1, name: 'Score',
        nameTextStyle: { color: tc.axisLabel, fontSize: 10 },
        axisLabel: { color: tc.axisLabel, fontSize: 10 },
        splitLine: { lineStyle: { color: tc.splitLine } } }] : []),
    ],
    dataZoom: [
      { type: 'slider', xAxisIndex: hasScores ? [0, 1] : [0],
        bottom: 8, height: 24,
        borderColor: tc.dataZoomBorder, backgroundColor: tc.dataZoomBg,
        fillerColor: tc.dataZoomFiller,
        handleStyle: { color: '#6366f1' },
        textStyle: { color: tc.dataZoomText } },
      { type: 'inside', xAxisIndex: hasScores ? [0, 1] : [0],
        zoomOnMouseWheel: true, moveOnMouseMove: false, moveOnMouseWheel: false },
    ],
    series,
  }
})
```

### D.4 Exposed methods
```ts
function zoomToRange(start: string, end: string) {
  const ch = chartRef.value?.chart; if (!ch) return
  const a = new Date(start).getTime(), b = new Date(end).getTime()
  const pad = Math.max((b - a) * 2, 3600000)
  ch.dispatchAction({ type: 'dataZoom',
    startValue: new Date(a - pad).toISOString(),
    endValue:   new Date(b + pad).toISOString() })
}
function resetZoom() { chartRef.value?.chart?.dispatchAction({ type: 'dataZoom', start: 0, end: 100 }) }
function getZoomRange() {
  const opt = chartRef.value?.chart?.getOption()
  const dz = (opt?.dataZoom as any)?.[0]
  if (!dz || dz.start == null) return null
  return { start: dz.start, end: dz.end }
}
function restoreZoom(r: { start: number; end: number }) {
  chartRef.value?.chart?.dispatchAction({ type: 'dataZoom', start: r.start, end: r.end })
}
defineExpose({ zoomToRange, resetZoom, getZoomRange, restoreZoom })
```

---

# Appendix E — Acceptance Tests (concrete scenarios)

In addition to the criteria in section 14:

1. **Chunked upload** — given a 10 MB CSV, the client must issue ≥5 chunks, each chunk POST returns `{ chunks_received: N }`. After complete, WebSocket emits `progress` (parsing) reaching `{progress: 100, stage: "parsing"}` and a final `complete`.
2. **NODE_NAME parsing** — uploading a CSV with column `NODE_NAME` whose values are 11-char alnum strings creates four extra dimension columns `NODE_DEVICE_TYPE` (3 chars), `NODE_POOL` (2), `NODE_LOCATION` (3), `NODE_CUSTOMER_TYPE` (3); rows whose value doesn't match get NaN in the new columns.
3. **KPI** — `(VS.Success / VS.Attempts) * 100` validates and computes per row after aggregation. Validation against a column that doesn't exist returns 400 with `Unrecognised variable(s): X`.
4. **Threshold semantics**:
   - quantile 0.95 → cutoff = 95th percentile of positive scores; ~5% flagged.
   - threshold 1.5 → fixed cutoff 1.5.
   - iqr 1.5 → cutoff = Q3 + 1.5×(Q3-Q1).
5. **Severity boundaries** — score = 1.4×threshold → low; 1.6×threshold → medium; 2.5×threshold → high.
6. **Persistence damping** — with `damping=0.5, min_anomaly_points=3`: a region of 4 points with `avg_score=1.0` and global threshold `1.0` yields `effective = 1 × (1 + 0.5 × log2(4)) = 2.0`; reclassified to high.
7. **Volume gate** — anomaly point at `t` with `volume_metric[t] = 5` is dropped if `volume_gate_threshold = 10`.
8. **LTTB** — `total_raw_points > max_points` → response sets `downsampled: true` and `series[*].timestamps.length <= max_points`. First and last timestamp of each series are preserved.
9. **WebSocket** — closing the socket triggers reconnect with delays 1000, 2000, 4000, 8000, 16000, 16000, … ms. Manual `disconnect()` does not reconnect.
10. **Theme** — toggling theme writes `localStorage["theme"]` and updates `<html data-theme="light|dark">`; chart re-renders with new colors via `themeVersion` increment.
11. **Clear** — clicking Clear: DELETEs session, removes both `dataset-selections:{sid}` and `model-selection:{sid}` from sessionStorage, resets all four Pinia stores, and `router.push({ name: 'upload' })`.
12. **Foundation downsample** — TimesFM/Chronos2 input with 9000 points downsamples to step=3 (~3000 points) before fitting.
13. **GPU** — when `_cached_accelerator()` returns `"mps"`, all DL forecasters are constructed with `pl_trainer_kwargs={"accelerator": "mps", "enable_progress_bar": False}` and the input series is cast to `float32`.

End of specification.
