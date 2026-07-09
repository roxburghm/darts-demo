import logging
import math

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ..models.schemas import (
    TimeSeriesRequest,
    TimeSeriesResponse,
    ExportCsvRequest,
)
from ..services.session_manager import session_manager


def _clean_values(values: list) -> list:
    """Replace NaN/Inf with None and ensure all values are JSON-serializable."""
    out = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        # Convert numpy scalars to Python native first
        if hasattr(v, 'item'):
            v = v.item()
        # Handle pandas NA
        try:
            import pandas as pd
            if pd.isna(v):
                out.append(None)
                continue
        except (TypeError, ValueError):
            pass
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out.append(None)
        else:
            out.append(v)
    return out

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/viz", tags=["visualization"])


def _build_series_list(df, ts_col, metrics, dimensions, max_points, name_suffix=""):
    """Build serialized series list from a DataFrame.

    Returns (series_list, was_downsampled).
    """
    from ..services.downsampler import lttb_downsample

    series_list = []
    downsampled = False

    if dimensions and len(dimensions) > 0:
        for group_key, group_df in df.groupby(dimensions, observed=True):
            if not isinstance(group_key, tuple):
                group_key = (group_key,)
            label_parts = [f"{c}={v}" for c, v in zip(dimensions, group_key)]
            label_prefix = " | ".join(label_parts)

            for metric in metrics:
                if metric not in group_df.columns:
                    continue
                # Keep null rows so gaps in the data survive to the chart
                series_df = group_df[[ts_col, metric]].sort_values(ts_col)
                timestamps = series_df[ts_col].astype(str).tolist()
                # Clean (NaN -> None) before downsampling so LTTB's null handling works
                values = _clean_values(series_df[metric].tolist())

                if len(values) > max_points:
                    timestamps, values = lttb_downsample(timestamps, values, max_points)
                    downsampled = True

                series_list.append({
                    "name": f"{label_prefix} | {metric}{name_suffix}",
                    "timestamps": timestamps,
                    "values": values,
                })
    else:
        for metric in metrics:
            if metric not in df.columns:
                continue
            # Keep null rows so gaps in the data survive to the chart
            series_df = df[[ts_col, metric]].sort_values(ts_col)
            timestamps = series_df[ts_col].astype(str).tolist()
            # Clean (NaN -> None) before downsampling so LTTB's null handling works
            values = _clean_values(series_df[metric].tolist())

            if len(values) > max_points:
                timestamps, values = lttb_downsample(timestamps, values, max_points)
                downsampled = True

            series_list.append({
                "name": f"{metric}{name_suffix}",
                "timestamps": timestamps,
                "values": values,
            })

    return series_list, downsampled


@router.post("/{session_id}/timeseries", response_model=TimeSeriesResponse)
async def get_timeseries(session_id: str, request: TimeSeriesRequest):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] != "ready":
        raise HTTPException(400, f"Dataset not ready, status: {metadata['status']}")

    try:
        return _process_timeseries(session_id, request, metadata)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Timeseries endpoint failed: %s", e)
        raise HTTPException(500, detail=str(e)) from e


def _process_timeseries(session_id: str, request: TimeSeriesRequest, metadata: dict) -> TimeSeriesResponse:
    import pandas as pd
    from ..storage.parquet_store import parquet_store
    from ..services.aggregator import aggregate_data
    from ..services.kpi_computer import compute_kpis, get_kpi_source_columns

    dataset_meta = metadata["dataset"]
    ts_col = dataset_meta["timestamp_column"]
    kpi_defs = dataset_meta.get("kpi_definitions", [])

    all_metric_names = [c["name"] for c in dataset_meta["metric_columns"]]
    kpi_names = {k["name"] for k in kpi_defs} if kpi_defs else set()
    base_metrics = [m for m in request.metrics if m not in kpi_names]

    columns = [ts_col] + base_metrics
    if request.dimensions:
        columns += request.dimensions

    if kpi_defs:
        selected_kpis = [k for k in kpi_defs if k["name"] in request.metrics]
        if selected_kpis:
            src_cols = get_kpi_source_columns(selected_kpis, all_metric_names)
            columns += src_cols

    df = parquet_store.read(session_id, columns=list(set(columns)))
    # Ensure clean RangeIndex — parquet may carry a stale index from ingestion
    df = df.reset_index(drop=True)

    if request.dimensions:
        request.dimensions = [d for d in request.dimensions if d in df.columns]

    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    df = df.dropna(subset=[ts_col])

    if request.dimension_filters:
        for col, values in request.dimension_filters.items():
            if col in df.columns:
                df = df[df[col].isin(values)]

    if request.time_start:
        t_start = pd.to_datetime(request.time_start).tz_localize(None)
        df = df[df[ts_col] >= t_start]
    if request.time_end:
        t_end = pd.to_datetime(request.time_end).tz_localize(None)
        df = df[df[ts_col] <= t_end]

    # Reset after all filtering so downstream code never hits index mismatches
    df = df.reset_index(drop=True)

    agg_metrics = [m for m in request.metrics if m in df.columns]
    if kpi_defs:
        kpi_names = {k["name"] for k in kpi_defs}
        selected_kpis = [k for k in kpi_defs if k["name"] in request.metrics]
        if selected_kpis:
            src_cols = get_kpi_source_columns(selected_kpis, all_metric_names)
            for c in src_cols:
                if c not in agg_metrics and c in df.columns:
                    agg_metrics.append(c)

    df = aggregate_data(
        df, ts_col, agg_metrics, request.aggregation, request.dimensions,
        preserve_gaps=True,
    )

    if kpi_defs:
        selected_kpis = [k for k in kpi_defs if k["name"] in request.metrics]
        if selected_kpis:
            df = compute_kpis(df, selected_kpis)

    # Apply infill before smoothing/transforms
    chart_metrics = [m for m in request.metrics if m in df.columns]
    infill = getattr(request, "infill", "none")
    if infill and infill != "none" and chart_metrics:
        from ..services.darts.runner import apply_infill
        df = apply_infill(df, chart_metrics, infill, ts_col=ts_col)

    # Apply smoothing
    if request.smoothing_window > 1 and chart_metrics:
        for col in chart_metrics:
            df[col] = df[col].rolling(
                window=request.smoothing_window, min_periods=1, center=True,
            ).mean()

    # Capture pre-transform data for overlay, then apply transforms
    has_transforms = bool(request.transforms) and bool(chart_metrics)
    original_df = None
    if has_transforms:
        original_df = df.copy()
        from ..services.darts.runner import apply_transforms
        df = apply_transforms(df, chart_metrics, request.transforms)

    total_raw = len(df)
    series_list, downsampled = _build_series_list(
        df, ts_col, request.metrics, request.dimensions, request.max_points,
    )

    # Build original (pre-transform) series for overlay comparison
    original_series_list = None
    if original_df is not None:
        original_series_list, _ = _build_series_list(
            original_df, ts_col, request.metrics, request.dimensions,
            request.max_points, name_suffix=" (original)",
        )

    return TimeSeriesResponse(
        series=series_list,
        original_series=original_series_list,
        total_raw_points=total_raw,
        downsampled=downsampled,
    )


@router.post("/{session_id}/export-csv")
async def export_csv(session_id: str, request: ExportCsvRequest):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] != "ready":
        raise HTTPException(400, f"Dataset not ready, status: {metadata['status']}")

    from ..storage.parquet_store import parquet_store
    from ..services.kpi_computer import compute_kpis, get_kpi_source_columns
    import pandas as pd
    import io

    dataset_meta = metadata["dataset"]
    ts_col = dataset_meta["timestamp_column"]
    kpi_defs = dataset_meta.get("kpi_definitions", [])
    all_metric_names = [c["name"] for c in dataset_meta["metric_columns"]]
    kpi_names = {k["name"] for k in kpi_defs} if kpi_defs else set()
    base_metrics = [m for m in request.metrics if m not in kpi_names]

    columns = [ts_col] + base_metrics
    if request.dimensions:
        columns += request.dimensions

    if kpi_defs:
        selected_kpis = [k for k in kpi_defs if k["name"] in request.metrics]
        if selected_kpis:
            columns += get_kpi_source_columns(selected_kpis, all_metric_names)

    df = parquet_store.read(session_id, columns=list(set(columns)))
    df = df.reset_index(drop=True)

    if request.dimensions:
        request.dimensions = [d for d in request.dimensions if d in df.columns]

    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    df = df.dropna(subset=[ts_col]).reset_index(drop=True)

    if request.dimension_filters:
        for col, values in request.dimension_filters.items():
            if col in df.columns:
                df = df[df[col].isin(values)]

    if request.time_start:
        t_start = pd.to_datetime(request.time_start).tz_localize(None)
        df = df[df[ts_col] >= t_start]
    if request.time_end:
        t_end = pd.to_datetime(request.time_end).tz_localize(None)
        df = df[df[ts_col] <= t_end]

    df = df.reset_index(drop=True)

    if kpi_defs:
        selected_kpis = [k for k in kpi_defs if k["name"] in request.metrics]
        if selected_kpis:
            df = compute_kpis(df, selected_kpis)

    output_cols = [ts_col]
    if request.dimensions:
        output_cols += request.dimensions
    output_cols += [m for m in request.metrics if m in df.columns]
    df = df[output_cols].sort_values(ts_col)

    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=raw-export.csv"},
    )
