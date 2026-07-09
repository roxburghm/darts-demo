import pandas as pd
from ..models.enums import AggregationLevel

# Map enum to pandas resample rule
AGG_RULES = {
    AggregationLevel.FIFTEEN_MIN: "15min",
    AggregationLevel.THIRTY_MIN: "30min",
    AggregationLevel.HOURLY: "1h",
    AggregationLevel.FOUR_HOUR: "4h",
    AggregationLevel.DAILY: "1D",
    "15min": "15min",
    "30min": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}


def collapse_by_timestamp(
    df: pd.DataFrame,
    timestamp_col: str,
    metric_cols: list[str],
    dimension_cols: list[str] | None = None,
    preserve_gaps: bool = False,
) -> pd.DataFrame:
    """
    Collapse rows that share the same timestamp.
    When dimension_cols are provided, group by (timestamp + dimensions) and sum
    within each group.  When no dimensions, sum across all entities at each timestamp.

    When ``preserve_gaps`` is True, groups where every value is null stay null
    (rather than summing to 0) so genuine data gaps survive to the chart.
    """
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
    df = df.dropna(subset=[timestamp_col]).reset_index(drop=True)

    valid_metrics = [c for c in metric_cols if c in df.columns]
    if not valid_metrics:
        return df

    group_cols = [timestamp_col]
    if dimension_cols:
        valid_dims = [d for d in dimension_cols if d in df.columns]
        group_cols += valid_dims

    min_count = 1 if preserve_gaps else 0
    result = (
        df.groupby(group_cols, observed=True)[valid_metrics]
        .sum(min_count=min_count)
        .reset_index()
    )
    return result.sort_values(timestamp_col)


def aggregate_data(
    df: pd.DataFrame,
    timestamp_col: str,
    metric_cols: list[str],
    aggregation: str | AggregationLevel,
    dimension_cols: list[str] | None = None,
    preserve_gaps: bool = False,
) -> pd.DataFrame:
    """
    Aggregate time series data to a coarser time granularity.
    Always sums within each group (with or without dimensions).

    When ``preserve_gaps`` is True, buckets with no data (empty or all-null)
    stay null instead of collapsing to 0, so gaps survive to the chart.
    """
    rule = AGG_RULES.get(aggregation)
    if rule is None:
        # RAW — still collapse duplicate timestamps (e.g. multiple nodes)
        return collapse_by_timestamp(
            df, timestamp_col, metric_cols, dimension_cols, preserve_gaps,
        )

    # Ensure timestamp is datetime
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
    df = df.dropna(subset=[timestamp_col]).reset_index(drop=True)
    df = df.set_index(timestamp_col)

    valid_metrics = [col for col in metric_cols if col in df.columns]
    if not valid_metrics:
        # No valid metric columns — return timestamps only
        result = df[[]]  # empty frame with datetime index
        result = result.resample(rule).size().to_frame("_count").reset_index()
        result = result.rename(columns={"index": timestamp_col} if "index" in result.columns else {})
        return result

    min_count = 1 if preserve_gaps else 0

    if dimension_cols:
        valid_dims = [d for d in dimension_cols if d in df.columns]
        if valid_dims:
            result = (
                df.groupby(valid_dims, observed=True)[valid_metrics]
                .resample(rule)
                .sum(min_count=min_count)
                .reset_index()
            )
            return result

    result = df[valid_metrics].resample(rule).sum(min_count=min_count).reset_index()
    result = result.rename(columns={"index": timestamp_col} if "index" in result.columns else {})
    return result
