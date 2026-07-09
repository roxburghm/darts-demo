# Anomaly Detection Playground

A self-service anomaly detection tool for time series data. Upload a CSV or Parquet file, select from 68 detection models, and visualise anomalies — all in the browser.

**Stack:** FastAPI (Python) + Vue 3 (TypeScript) + [Darts](https://github.com/unit8co/darts) + [PyOD](https://github.com/yzhao062/pyod) + ECharts

---

## Quick Start

### Docker (recommended)

```bash
docker compose up --build
```

Open [http://localhost:8090](http://localhost:8090).

> Docker Desktop on macOS cannot access Apple Silicon GPU. For GPU acceleration, run natively (see below).

### Native Development

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[torch,peer]"   # includes PyTorch + foundation models + peer analysis extras
uvicorn app.main:app --reload --port 8001

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

Or use the dev script:

```bash
./dev.sh    # starts both backend (8001) and frontend (5173)
```

---

## Workflow

The app guides you through five steps:

| Step | Page | What happens |
|------|------|-------------|
| 1 | **Upload** | Drag-and-drop a CSV or Parquet file (up to 500 MB). Chunked upload with real-time parsing progress. |
| 2 | **Preview** | Inspect column types, row counts, null percentages, and sample data. |
| 3 | **Configure** | Select metrics and dimensions, set aggregation level, define custom KPIs, preview charts with transforms. |
| 4 | **Models** | Browse 68 models with search, GPU/Foundation/Compatible filters, and a condensed list view. Select a model and tune its parameters. |
| 5 | **Analysis** | Run detection, view anomaly scores overlaid on time series charts, adjust thresholds live, and export results as CSV. |

The breadcrumb steps in the header are **navigable** — click any completed step to go back. Use the **Clear** button (top-right) to delete all data and start over.

---

## Models

68 models across three categories:

- **40 Anomaly Scorers** — compute scores directly (statistical, density-based, deep learning, foundation models, peer/cohort analysis)
- **28 Forecast Models** — predict expected values; anomalies are detected when actuals deviate from predictions

21 models support **GPU acceleration** (Apple Silicon MPS or NVIDIA CUDA). 5 are **foundation models** with zero-shot capability.

### Peer / Cohort Analysis

6 models compare individual groups (e.g. nodes) against the behaviour of their peers. Select a dimension (e.g. `NODE_NAME`) and these models flag groups that diverge from the cohort:

| Model | What it detects |
|-------|----------------|
| **Peer Divergence** | Point-by-point deviation from consensus (MAD, percentage, or z-score normalization) |
| **Peer PCA Reconstruction** | Nodes whose overall pattern can't be explained by the shared group behaviour |
| **Peer Functional Depth** | Nodes whose entire trajectory lies outside the group envelope (Modified Band Depth) |
| **Peer Feature Isolation** | Lost periodicity, entropy shifts, and trend changes — feature-based Isolation Forest |
| **Peer DTW + LOF** | Time-shifted patterns via Dynamic Time Warping + Local Outlier Factor |
| **Peer Matrix Profile** | Novel subsequence shapes not found in the group norm (STUMPY) |

See [MODELS.md](MODELS.md) for the full catalog.

---

## Custom KPIs

Define derived metrics using formulas that reference existing columns. KPIs are computed on-the-fly after aggregation and saved to the session metadata (not the parquet file).

**Formula engine:** [`pandas.eval()`](https://pandas.pydata.org/docs/reference/api/pandas.eval.html) — column names with dots or spaces are auto-wrapped in backticks.

| Category | Supported |
|----------|-----------|
| **Arithmetic** | `+` `-` `*` `/` `**` `//` `%` |
| **Comparison** | `>` `<` `>=` `<=` `==` `!=` |
| **Logic** | `&` (and) `\|` (or) `~` (not) |
| **Functions** | `abs()` `sqrt()` `log()` `log10()` `exp()` `sin()` `cos()` `tan()` |

**Not supported:** `max()`, `min()`, `if`/`else`, or arbitrary Python functions.

**Examples:**

```
VS.Success / VS.Attempts * 100          # success rate percentage
abs(metric_a - metric_b)                 # absolute difference
(upload + download) / 2                  # average of two metrics
sqrt(metric_x ** 2 + metric_y ** 2)      # Euclidean magnitude
log10(throughput + 1)                    # log-scaled metric
```

KPIs are validated against a sample of your data when saved. Invalid formulas show an error message.

---

## Configuration

Backend settings are configured via environment variables with the `DAD_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `DAD_SESSION_TTL_HOURS` | `24` | Auto-cleanup sessions after this many hours |
| `DAD_MAX_UPLOAD_SIZE_MB` | `500` | Maximum upload file size |
| `DAD_MAX_CHART_POINTS` | `3000` | Max data points returned for charting |

---

## API

All endpoints are under `/api`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload/init` | Initialise chunked upload |
| `POST` | `/upload/{id}/chunk` | Upload a file chunk |
| `POST` | `/upload/{id}/complete` | Finalise upload and trigger parsing |
| `GET` | `/upload/{id}/status` | Polling fallback for parse progress |
| `GET` | `/datasets/{id}` | Dataset metadata |
| `GET` | `/datasets/{id}/preview` | Sample rows |
| `GET` | `/datasets/{id}/download` | Download parsed Parquet |
| `DELETE` | `/datasets/{id}` | Delete all session data |
| `GET` | `/models/` | List all models with params |
| `POST` | `/models/{id}/compatibility` | Check which models fit your data |
| `POST` | `/models/{id}/detect` | Trigger anomaly detection |
| `GET` | `/models/{id}/results/{run}` | Fetch detection results |
| `POST` | `/viz/{id}/timeseries` | Time series data for charting |
| `POST` | `/viz/{id}/export-csv` | Export results as CSV |
| `WS` | `/ws/{id}` | Real-time progress updates |

---

## Privacy & Data Handling

Your data is cached temporarily on the server for the duration of your session and is used solely for analysis. It is **not** stored permanently, shared, or used in any other way.

- **Clear button** — instantly deletes all server-side data (uploads, parsed files, results) and resets the browser session
- **Re-upload** — uploading a new file creates a new session; old sessions are cleaned up automatically
- **Auto-cleanup** — expired sessions are purged every 30 minutes (default TTL: 24 hours)

---

## Project Structure

```
darts-demo/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   ├── models/           # Pydantic schemas & enums
│   │   ├── services/         # Business logic
│   │   │   └── darts/        # Model registry, runner, compatibility
│   │   ├── storage/          # Parquet store, result cache
│   │   ├── utils/            # Cleanup, progress broadcasting
│   │   ├── config.py         # Settings (env-based)
│   │   └── main.py           # FastAPI app
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/              # Axios client & typed API calls
│   │   ├── stores/           # Pinia stores (upload, dataset, models, analysis)
│   │   ├── views/            # 5 workflow step pages
│   │   ├── components/       # Reusable UI (charts, cards, panels, layout)
│   │   ├── router/           # Vue Router
│   │   └── styles/           # CSS variables & themes
│   ├── package.json
│   └── vite.config.ts
├── Dockerfile                # Multi-stage production build
├── docker-compose.yml
├── dev.sh                    # Dev server launcher
├── MODELS.md                 # Full model catalog
└── README.md
```

---

## GPU Acceleration

21 models support GPU acceleration:

- **Apple Silicon (MPS):** Detected automatically when running natively
- **NVIDIA CUDA:** Detected automatically on Linux with CUDA drivers
- **CPU fallback:** All GPU models work on CPU if no GPU is available

### Peer Analysis Extras

DTW + LOF and Matrix Profile require optional dependencies:

```bash
pip install -e ".[peer]"        # installs dtaidistance + stumpy
```

The other 4 peer models (Divergence, PCA, Functional Depth, Feature Isolation) work with no extra dependencies.

### Foundation Model Extras

MOMENT and Lag-Llama require separate installation due to dependency conflicts:

```bash
pip install momentfm --no-deps
pip install lag-llama --no-deps
```

---

## Development

```bash
# Type-check frontend
cd frontend && npx vue-tsc --noEmit

# Lint frontend
npm run lint

# Run backend tests
cd backend && pytest

# Lint backend
ruff check app/
```
