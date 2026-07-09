import math
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..models.schemas import DatasetMetadata, DimensionValuesResponse, KPIDefinition, KPIValidateRequest
from ..services.session_manager import session_manager
from ..config import settings


def _sanitize_value(v):
    """Convert numpy/pandas types to JSON-safe Python primitives."""
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    # numpy int/float → Python int/float
    try:
        if hasattr(v, 'item'):
            return v.item()
    except (ValueError, OverflowError):
        return str(v)
    # pandas Timestamp → ISO string
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    return v


def _sanitize_rows(records: list[dict]) -> list[dict]:
    return [{k: _sanitize_value(v) for k, v in row.items()} for row in records]

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete all server-side data for a session."""
    session_manager.cleanup_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}", response_model=DatasetMetadata)
async def get_dataset_metadata(session_id: str):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] != "ready":
        raise HTTPException(400, f"Dataset not ready, status: {metadata['status']}")

    dataset_meta = metadata.get("dataset")
    if dataset_meta is None:
        raise HTTPException(500, "Dataset metadata missing")

    return DatasetMetadata(**dataset_meta)


@router.get("/{session_id}/download")
async def download_parquet(session_id: str):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] != "ready":
        raise HTTPException(400, f"Dataset not ready, status: {metadata['status']}")

    parquet_path = settings.parsed_dir / session_id / "data.parquet"
    if not parquet_path.exists():
        raise HTTPException(404, "Parquet file not found")

    # Embed KPI definitions in Parquet file metadata for round-trip persistence
    kpi_defs = metadata.get("dataset", {}).get("kpi_definitions", [])
    if kpi_defs:
        import json
        import pyarrow.parquet as pq
        table = pq.read_table(str(parquet_path))
        existing_meta = table.schema.metadata or {}
        existing_meta[b"kpi_definitions"] = json.dumps(kpi_defs).encode("utf-8")
        table = table.replace_schema_metadata(existing_meta)
        # Write to a temp file for download (don't modify the stored file)
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
        pq.write_table(table, tmp.name, compression="snappy")
        download_path = tmp.name
    else:
        download_path = str(parquet_path)

    # Derive download filename from original upload name
    original = metadata.get("filename", "dataset")
    stem = Path(original).stem
    download_name = f"{stem}.parquet"

    return FileResponse(
        path=download_path,
        media_type="application/octet-stream",
        filename=download_name,
    )


@router.put("/{session_id}/kpis")
async def save_kpis(session_id: str, kpis: list[KPIDefinition]):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] != "ready":
        raise HTTPException(400, f"Dataset not ready, status: {metadata['status']}")

    # Validate each formula against real data
    from ..storage.parquet_store import parquet_store
    from ..services.kpi_computer import validate_kpi

    df = parquet_store.read(session_id, limit=100)
    errors = {}
    for kpi in kpis:
        err = validate_kpi(df, kpi.formula)
        if err:
            errors[kpi.name] = err

    if errors:
        raise HTTPException(400, detail={"message": "Invalid KPI formulas", "errors": errors})

    # Save to metadata
    kpi_dicts = [kpi.model_dump() for kpi in kpis]
    dataset_meta = metadata.get("dataset", {})
    dataset_meta["kpi_definitions"] = kpi_dicts
    session_manager.update_metadata(session_id, {"dataset": dataset_meta})

    return {"status": "ok", "kpi_count": len(kpis)}


@router.post("/{session_id}/kpis/validate")
async def validate_kpi_formula(session_id: str, body: KPIValidateRequest):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] != "ready":
        raise HTTPException(400, f"Dataset not ready, status: {metadata['status']}")

    from ..storage.parquet_store import parquet_store
    from ..services.kpi_computer import validate_kpi

    df = parquet_store.read(session_id, limit=100)
    err = validate_kpi(df, body.formula)
    if err:
        return {"valid": False, "error": err}
    return {"valid": True}


@router.get("/{session_id}/preview")
async def get_preview(session_id: str, rows: int = 100):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] != "ready":
        raise HTTPException(400, f"Dataset not ready, status: {metadata['status']}")

    from ..storage.parquet_store import parquet_store
    df = parquet_store.read(session_id, limit=rows)
    return {
        "columns": df.columns.tolist(),
        "rows": _sanitize_rows(df.head(rows).to_dict(orient="records")),
        "total_rows": metadata["dataset"]["row_count"],
    }


@router.get("/{session_id}/dimension-values", response_model=list[DimensionValuesResponse])
async def get_dimension_values(session_id: str):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] != "ready":
        raise HTTPException(400, f"Dataset not ready, status: {metadata['status']}")

    from ..storage.parquet_store import parquet_store
    dataset_meta = metadata["dataset"]
    dim_cols = [c["name"] for c in dataset_meta["dimension_columns"]]

    results = []
    df = parquet_store.read(session_id, columns=dim_cols)
    for col in dim_cols:
        values = sorted(df[col].dropna().unique().tolist())
        results.append(DimensionValuesResponse(column=col, values=values, count=len(values)))

    return results
