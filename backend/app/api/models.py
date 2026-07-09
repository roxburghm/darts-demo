"""API endpoints for the Darts model registry, compatibility checking, and detection."""

import uuid
import asyncio
import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..models.schemas import (
    ModelInfo,
    CompatibilityRequest,
    CompatibilityResponse,
    DartsDetectionConfig,
    DartsAnomalyResult,
)
from ..services.session_manager import session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/", response_model=list[ModelInfo])
async def list_models():
    """Return all available Darts models with metadata and parameter definitions."""
    from ..services.darts.registry import get_all_models
    return get_all_models()


@router.post("/{session_id}/compatibility", response_model=CompatibilityResponse)
async def check_model_compatibility(session_id: str, request: CompatibilityRequest):
    """Check which models are compatible with the user's data configuration."""
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] != "ready":
        raise HTTPException(400, "Dataset not ready")

    from ..storage.parquet_store import parquet_store
    from ..services.aggregator import aggregate_data

    dataset_meta = metadata["dataset"]
    ts_col = dataset_meta["timestamp_column"]

    # Read just enough to count effective data points
    kpi_defs = dataset_meta.get("kpi_definitions", [])
    kpi_names = {k["name"] for k in kpi_defs}
    base_metrics = [m for m in request.metrics if m not in kpi_names]

    columns = [ts_col] + base_metrics
    if request.dimensions:
        columns += request.dimensions

    df = parquet_store.read(session_id, columns=list(set(columns)))

    # Apply dimension filters
    if request.dimension_filters:
        for col, values in request.dimension_filters.items():
            if col in df.columns:
                df = df[df[col].isin(values)]

    agg_metrics = [m for m in request.metrics if m in df.columns]

    # Count dimensions and unique groups BEFORE aggregation (raw df still has dim cols)
    num_dimensions = len(request.dimensions) if request.dimensions else 0
    num_dimension_groups = 0
    if request.dimensions and len(request.dimensions) > 0:
        dim_col = request.dimensions[0]
        if dim_col in df.columns:
            num_dimension_groups = df[dim_col].nunique()

    # Aggregate WITHOUT dimensions to get effective data points per time series
    # (peer models operate per-group, so per-group row count is what matters)
    df_agg = aggregate_data(df, ts_col, agg_metrics, request.aggregation)
    num_data_points = len(df_agg)
    num_metrics = len(request.metrics)

    from ..services.darts.compatibility import check_compatibility
    results = check_compatibility(
        num_metrics, num_data_points, num_dimensions, num_dimension_groups,
    )

    return CompatibilityResponse(models=results)


@router.post("/{session_id}/detect")
async def trigger_detection(
    session_id: str,
    config: DartsDetectionConfig,
    background_tasks: BackgroundTasks,
):
    """Trigger Darts anomaly detection in the background."""
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] != "ready":
        raise HTTPException(400, "Dataset not ready")

    run_id = uuid.uuid4().hex[:12]
    background_tasks.add_task(_run_detection, session_id, run_id, config)

    return {"run_id": run_id, "status": "running"}


async def _run_detection(session_id: str, run_id: str, config: DartsDetectionConfig):
    """Background task that runs Darts detection."""
    from ..services.darts.runner import run_darts_detection
    from ..storage.parquet_store import parquet_store
    from ..services.aggregator import aggregate_data
    from ..services.kpi_computer import compute_kpis, get_kpi_source_columns
    from ..utils.progress import progress_broadcaster
    from ..storage.result_cache import result_cache

    try:
        await progress_broadcaster.send_progress(session_id, "analysis", 10, "Loading data...")

        metadata = session_manager.get_metadata(session_id)
        dataset_meta = metadata["dataset"]
        ts_col = dataset_meta["timestamp_column"]
        kpi_defs = dataset_meta.get("kpi_definitions", [])
        all_metric_names = [c["name"] for c in dataset_meta["metric_columns"]]

        # Build column list
        kpi_names = {k["name"] for k in kpi_defs}
        columns = [ts_col] + [m for m in config.metrics if m not in kpi_names]
        if config.dimensions:
            columns += list(config.dimensions)
        if kpi_defs:
            selected_kpis = [k for k in kpi_defs if k["name"] in config.metrics]
            if selected_kpis:
                columns += get_kpi_source_columns(selected_kpis, all_metric_names)

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None, parquet_store.read, session_id, list(set(columns))
        )

        # Apply dimension filters
        if config.dimension_filters:
            for col, values in config.dimension_filters.items():
                if col in df.columns:
                    df = df[df[col].isin(values)]

        await progress_broadcaster.send_progress(session_id, "analysis", 20, "Aggregating...")

        # Aggregate
        import pandas as pd
        agg_metrics = [m for m in config.metrics if m in df.columns]
        if kpi_defs:
            for k in kpi_defs:
                if k["name"] in config.metrics:
                    for c in get_kpi_source_columns([k], all_metric_names):
                        if c not in agg_metrics and c in df.columns:
                            agg_metrics.append(c)

        df = aggregate_data(df, ts_col, agg_metrics, config.aggregation, config.dimensions)

        # Compute KPIs
        if kpi_defs:
            selected_kpis = [k for k in kpi_defs if k["name"] in config.metrics]
            if selected_kpis:
                df = compute_kpis(df, selected_kpis)

        await progress_broadcaster.send_progress(session_id, "analysis", 40, "Running Darts model...")

        def _progress_cb(pct, msg):
            try:
                future = asyncio.run_coroutine_threadsafe(
                    progress_broadcaster.send_progress(
                        session_id, "analysis", 40 + pct * 0.5, msg
                    ),
                    loop,
                )
                future.result(timeout=1.0)
            except Exception:
                pass

        result = await loop.run_in_executor(
            None, run_darts_detection, df, ts_col, config, _progress_cb
        )
        result.run_id = run_id

        result_cache.save(session_id, run_id, result)

        await progress_broadcaster.send_complete(session_id, "analysis", {"run_id": run_id})
    except Exception as e:
        logger.exception("Detection failed for session %s", session_id)
        await progress_broadcaster.send_error(session_id, str(e))


@router.get("/{session_id}/results/{run_id}", response_model=DartsAnomalyResult)
async def get_results(session_id: str, run_id: str):
    """Fetch cached detection results."""
    from ..storage.result_cache import result_cache
    result = result_cache.load(session_id, run_id)
    if result is None:
        raise HTTPException(404, "Results not found")
    return result
