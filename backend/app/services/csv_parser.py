import asyncio
import logging
import re
import shutil
from pathlib import Path
import polars as pl
import pandas as pd

logger = logging.getLogger(__name__)

from .column_classifier import classify_columns
from .dimension_parser import expand_structured_dimensions
from .session_manager import session_manager
from ..storage.parquet_store import parquet_store
from ..utils.progress import progress_broadcaster
from ..config import settings


def detect_header_row(file_path: Path, max_lines: int = 15) -> int:
    """
    Detect the actual CSV header row by scanning the first N lines.
    Returns the 0-based index of the header row (lines to skip before it).

    Heuristics:
    - Header rows have all non-empty string fields
    - Header rows don't contain values that look like data (timestamps, numbers, "--")
    - Header rows typically have more comma-separated fields than superfluous lines
    """
    lines = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            lines.append(line.strip())

    if not lines:
        return 0

    # Count fields per line
    field_counts = []
    for line in lines:
        fields = line.split(",")
        field_counts.append(len(fields))

    # The header row typically has the most fields (or equal to data rows)
    max_fields = max(field_counts)

    # Patterns that indicate data (not headers)
    data_patterns = [
        re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}"),  # Timestamps
        re.compile(r"^--$"),  # Null indicators
        re.compile(r"^\d+\.\d+$"),  # Decimal numbers
        re.compile(r"^\d{10,}$"),  # Epoch timestamps
    ]

    for i, line in enumerate(lines):
        fields = [f.strip().strip('"') for f in line.split(",")]

        # Skip lines with too few fields
        if len(fields) < max_fields * 0.8:
            continue

        # Skip empty lines
        if all(f == "" for f in fields):
            continue

        # Check if this looks like a header:
        # - All fields are non-empty
        # - No field matches data patterns
        # - Fields look like identifiers (mostly alphabetic/underscore)
        all_non_empty = all(f != "" for f in fields)
        no_data_values = not any(
            any(p.match(f) for p in data_patterns)
            for f in fields
        )
        has_alpha_fields = sum(1 for f in fields if re.match(r"^[A-Za-z_]", f)) > len(fields) * 0.5

        if all_non_empty and no_data_values and has_alpha_fields:
            return i

    # Fallback: assume no superfluous lines
    return 0


def parse_csv(file_path: Path) -> tuple[pl.DataFrame, int]:
    """
    Parse a CSV file, handling superfluous header lines and null values.
    Returns (DataFrame, number_of_skipped_lines).
    """
    skip_rows = detect_header_row(file_path)

    df = pl.read_csv(
        file_path,
        skip_rows=skip_rows,
        null_values=["--", "", "NA", "N/A", "null", "NULL"],
        try_parse_dates=True,
        infer_schema_length=10000,
        ignore_errors=True,
    )

    # Clean column names: strip whitespace, remove quotes
    rename_map = {}
    for col in df.columns:
        cleaned = col.strip().strip('"').strip("'")
        if cleaned != col:
            rename_map[col] = cleaned
    if rename_map:
        df = df.rename(rename_map)

    return df, skip_rows


async def parse_csv_background(session_id: str, file_path: Path):
    """Background task that parses a CSV and stores as Parquet."""
    try:
        await progress_broadcaster.send_progress(session_id, "parsing", 5, "Detecting headers...")

        # Parse CSV (run in thread to not block event loop)
        loop = asyncio.get_event_loop()
        df, skip_rows = await loop.run_in_executor(None, parse_csv, file_path)

        await progress_broadcaster.send_progress(session_id, "parsing", 40, "Classifying columns...")

        # Convert to pandas for classification and storage
        pdf = df.to_pandas()

        # Classify columns
        classification = classify_columns(pdf)

        # Expand structured dimensions (e.g. NODE_NAME → device_type, pool, etc.)
        pdf, classification["dimension_columns"] = expand_structured_dimensions(
            pdf, classification["dimension_columns"]
        )

        # Deduplicate: keep last row for each timestamp + dimension group
        ts_col = classification["timestamp_column"]
        dim_cols = [c["name"] for c in classification["dimension_columns"]]
        if ts_col:
            dedup_cols = [ts_col] + dim_cols
            before = len(pdf)
            pdf = pdf.drop_duplicates(subset=dedup_cols, keep="last")
            dupes = before - len(pdf)
            if dupes > 0:
                pdf = pdf.reset_index(drop=True)

        await progress_broadcaster.send_progress(session_id, "parsing", 60, "Converting to optimized format...")

        # Store as Parquet
        await loop.run_in_executor(None, parquet_store.write, session_id, pdf)

        await progress_broadcaster.send_progress(session_id, "parsing", 85, "Saving metadata...")

        # Build metadata
        ts_col = classification["timestamp_column"]
        time_range = ("", "")
        if ts_col and ts_col in pdf.columns:
            ts_series = pd.to_datetime(pdf[ts_col], errors="coerce")
            valid_ts = ts_series.dropna()
            if len(valid_ts) > 0:
                time_range = (
                    str(valid_ts.min()),
                    str(valid_ts.max()),
                )

        dataset_meta = {
            "session_id": session_id,
            "filename": session_manager.get_metadata(session_id)["filename"],
            "row_count": len(pdf),
            "time_range": time_range,
            "timestamp_column": ts_col or "",
            "dimension_columns": classification["dimension_columns"],
            "metric_columns": classification["metric_columns"],
            "skipped_header_lines": skip_rows,
        }

        session_manager.update_metadata(session_id, {
            "status": "ready",
            "parsing_progress": 100,
            "dataset": dataset_meta,
        })

        # Clean up original CSV to save disk space
        try:
            file_path.unlink()
        except OSError:
            pass

        await progress_broadcaster.send_complete(session_id, "parsing")

    except Exception as e:
        session_manager.update_metadata(session_id, {
            "status": "error",
            "error": str(e),
        })
        await progress_broadcaster.send_error(session_id, str(e))


def _process_parquet_sync(file_path: Path) -> tuple[pd.DataFrame, list, dict]:
    """Synchronous Parquet processing — run in executor to avoid blocking event loop."""
    import json
    import gc
    import pyarrow.parquet as pq

    # Read schema metadata without loading the full table
    pq_file = pq.ParquetFile(str(file_path))
    pq_metadata = pq_file.schema_arrow.metadata or {}
    embedded_kpis = []
    if b"kpi_definitions" in pq_metadata:
        try:
            embedded_kpis = json.loads(pq_metadata[b"kpi_definitions"].decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # Read table and convert to pandas, then free the Arrow table
    table = pq_file.read()
    pdf = table.to_pandas()
    del table, pq_file
    gc.collect()

    # Convert object (string) columns to category dtype to reduce memory ~80%
    for col in pdf.columns:
        if pdf[col].dtype == object:
            pdf[col] = pdf[col].astype("category")

    classification = classify_columns(pdf)
    pdf, classification["dimension_columns"] = expand_structured_dimensions(
        pdf, classification["dimension_columns"]
    )

    ts_col = classification["timestamp_column"]
    dim_cols = [c["name"] for c in classification["dimension_columns"]]
    if ts_col:
        dedup_cols = [ts_col] + dim_cols
        before = len(pdf)
        pdf = pdf.drop_duplicates(subset=dedup_cols, keep="last")
        if before - len(pdf) > 0:
            pdf = pdf.reset_index(drop=True)

    return pdf, embedded_kpis, classification


async def process_parquet_background(session_id: str, file_path: Path):
    """Background task that processes an uploaded Parquet file (skip CSV parsing)."""
    try:
        await progress_broadcaster.send_progress(session_id, "parsing", 10, "Validating Parquet file...")

        loop = asyncio.get_event_loop()

        # Run all heavy processing in a thread to avoid blocking the event loop
        pdf, embedded_kpis, classification = await loop.run_in_executor(
            None, _process_parquet_sync, file_path
        )

        await progress_broadcaster.send_progress(session_id, "parsing", 60, "Storing dataset...")

        # Write the (possibly enriched) DataFrame to Parquet
        await loop.run_in_executor(None, parquet_store.write, session_id, pdf)

        # Clean up original upload
        try:
            file_path.unlink()
        except OSError:
            pass

        await progress_broadcaster.send_progress(session_id, "parsing", 85, "Saving metadata...")

        # Build metadata (same structure as CSV path)
        ts_col = classification["timestamp_column"]
        time_range = ("", "")
        if ts_col and ts_col in pdf.columns:
            ts_series = pd.to_datetime(pdf[ts_col], errors="coerce")
            valid_ts = ts_series.dropna()
            if len(valid_ts) > 0:
                time_range = (str(valid_ts.min()), str(valid_ts.max()))

        dataset_meta = {
            "session_id": session_id,
            "filename": session_manager.get_metadata(session_id)["filename"],
            "row_count": len(pdf),
            "time_range": time_range,
            "timestamp_column": ts_col or "",
            "dimension_columns": classification["dimension_columns"],
            "metric_columns": classification["metric_columns"],
            "skipped_header_lines": 0,
            "kpi_definitions": embedded_kpis,
        }

        session_manager.update_metadata(session_id, {
            "status": "ready",
            "parsing_progress": 100,
            "dataset": dataset_meta,
        })

        await progress_broadcaster.send_complete(session_id, "parsing")

    except Exception as e:
        session_manager.update_metadata(session_id, {
            "status": "error",
            "error": f"Invalid Parquet file: {e}",
        })
        await progress_broadcaster.send_error(session_id, str(e))
