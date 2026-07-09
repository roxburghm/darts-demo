import pandas as pd
import numpy as np

# Known dimension column names (case-insensitive)
KNOWN_DIMENSION_NAMES = {
    "node_name", "nodename", "node",
    "ne_version", "neversion",
    "network", "network_type", "network_name", "networkname",
    "moid", "mo_id",
    "mme_function", "mmefunction",
    "site", "site_name", "sitename",
    "cell", "cell_name", "cellname",
    "region", "area",
    "vendor",
    "technology", "tech",
    "customer_type", "customertype", "cust_type",
    "subscriber_type",
    "service_type", "servicetype",
    "interface", "link",
}

# Columns to discard — metadata/housekeeping that are neither dimensions
# nor useful metrics (case-insensitive)
KNOWN_IGNORE_NAMES = {
    "counter_group", "countergroup",
    "period_duration", "periodduration",
    "reliability_indicator", "reliabilityindicator",
    "granularity_period", "granularityperiod",
    "object_type", "objecttype",
}

# Known timestamp column names (case-insensitive)
KNOWN_TIMESTAMP_NAMES = {
    "timestamp", "time", "datetime", "date_time",
    "start_time", "starttime", "start",
    "end_time", "endtime",
    "period_start", "period_end",
    "collection_time", "collectiontime",
    "date",
}


def classify_columns(df: pd.DataFrame) -> dict:
    """
    Classify DataFrame columns into timestamp, dimension, and metric columns.

    Returns dict with:
        - timestamp_column: str | None
        - dimension_columns: list[dict] (ColumnInfo-like)
        - metric_columns: list[dict] (ColumnInfo-like)
    """
    timestamp_col = _detect_timestamp_column(df)
    dimension_cols = []
    metric_cols = []

    for col in df.columns:
        if col == timestamp_col:
            continue

        # Skip known housekeeping/metadata columns
        if col.lower().strip() in KNOWN_IGNORE_NAMES:
            continue

        col_info = _build_column_info(df, col)

        if _is_dimension_column(df, col):
            dimension_cols.append(col_info)
        elif _is_numeric_column(df, col):
            metric_cols.append(col_info)
        else:
            # Ambiguous columns default to dimension if string-like, else skip
            if _is_string_dtype(df[col]):
                dimension_cols.append(col_info)

    return {
        "timestamp_column": timestamp_col,
        "dimension_columns": dimension_cols,
        "metric_columns": metric_cols,
    }


def _is_string_dtype(series: pd.Series) -> bool:
    """Check if a series holds string data (object or category of strings)."""
    if series.dtype == object:
        return True
    if isinstance(series.dtype, pd.CategoricalDtype):
        return series.cat.categories.dtype == object
    return False


def _detect_timestamp_column(df: pd.DataFrame) -> str | None:
    """Find the timestamp column by name matching or dtype detection."""
    # First try known names
    for col in df.columns:
        if col.lower().strip() in KNOWN_TIMESTAMP_NAMES:
            return col

    # Then try datetime dtype
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col

    # Try parsing string columns as datetime
    for col in df.columns:
        if _is_string_dtype(df[col]):
            sample = df[col].dropna().head(20).astype(str)
            if len(sample) == 0:
                continue
            try:
                parsed = pd.to_datetime(sample, errors="coerce")
                if parsed.notna().sum() > len(sample) * 0.8:
                    # Convert the whole column
                    df[col] = pd.to_datetime(df[col].astype(str), errors="coerce")
                    return col
            except (ValueError, TypeError):
                continue

    return None


def _is_dimension_column(df: pd.DataFrame, col: str) -> bool:
    """Determine if a column is a dimension (categorical/grouping) column."""
    # Known name match
    if col.lower().strip() in KNOWN_DIMENSION_NAMES:
        return True

    # String dtype with low cardinality
    if _is_string_dtype(df[col]):
        n_unique = df[col].nunique()
        n_rows = len(df)
        # Low cardinality: fewer than 1% of rows, or fewer than 100 unique values
        if n_unique < max(n_rows * 0.01, 100):
            return True

    return False


def _is_numeric_column(df: pd.DataFrame, col: str) -> bool:
    """Check if a column is numeric (potential metric)."""
    return pd.api.types.is_numeric_dtype(df[col])


def _build_column_info(df: pd.DataFrame, col: str) -> dict:
    """Build a ColumnInfo dict for a column."""
    null_count = int(df[col].isna().sum())
    null_pct = null_count / len(df) if len(df) > 0 else 0.0

    # Sample values
    sample = df[col].dropna().head(5).tolist()
    # Convert numpy types to native Python types
    sample_values = []
    for v in sample:
        if isinstance(v, (np.integer,)):
            sample_values.append(int(v))
        elif isinstance(v, (np.floating,)):
            sample_values.append(float(v))
        elif isinstance(v, (np.bool_,)):
            sample_values.append(bool(v))
        else:
            sample_values.append(str(v))

    return {
        "name": col,
        "dtype": str(df[col].dtype),
        "null_count": null_count,
        "null_pct": round(null_pct, 4),
        "sample_values": sample_values,
    }
