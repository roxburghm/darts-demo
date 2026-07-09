"""
Parse structured dimension columns into synthetic sub-dimensions.

Telecom node naming conventions often encode device type, pool, location,
and customer type into a single identifier.  This module detects such
patterns and generates individual dimension columns so users can slice
data along each axis independently.

Currently supported patterns
-----------------------------
NODE_NAME / NODENAME / NODE  (case-insensitive):
    Format ``dddpplllccc`` where:
    - ``ddd``  = device type  (3 chars)
    - ``pp``   = pool         (2 chars)
    - ``lll``  = location     (3 chars)
    - ``ccc``  = customer type(3 chars)
    Total: 11 characters, all alphanumeric.
"""

import re
import pandas as pd

from .column_classifier import _build_column_info


# Columns eligible for NODE_NAME parsing (lowercase)
_NODE_NAME_ALIASES = {"node_name", "nodename", "node"}

# The expected total length for dddpplllccc
_NODE_NAME_LEN = 11

# Pattern: 3 alpha + 2 alnum + 3 alpha + 3 alpha  (relaxed: all alnum)
_NODE_NAME_RE = re.compile(r"^[A-Za-z0-9]{11}$")


def expand_structured_dimensions(
    df: pd.DataFrame,
    dimension_columns: list[dict],
) -> tuple[pd.DataFrame, list[dict]]:
    """Try to expand any structured dimension columns into sub-dimensions.

    Args:
        df: The DataFrame (modified in-place with new columns).
        dimension_columns: The current list of dimension ColumnInfo dicts.

    Returns:
        (df, updated_dimension_columns) — new synthetic columns are appended
        to the dimension list.
    """
    new_dims = []

    for dim_info in dimension_columns:
        col = dim_info["name"]
        if col.lower().strip() in _NODE_NAME_ALIASES:
            generated = _expand_node_name(df, col)
            new_dims.extend(generated)

    if new_dims:
        dimension_columns = dimension_columns + new_dims

    return df, dimension_columns


def _expand_node_name(df: pd.DataFrame, col: str) -> list[dict]:
    """Parse a NODE_NAME column into device_type, pool, location, customer_type.

    Only proceeds if ≥80% of non-null values match the expected 11-char
    pattern, so we don't corrupt data with a wrong assumption.
    """
    sample = df[col].dropna()
    if len(sample) == 0:
        return []

    # Check that most values match the expected format
    matches = sample.astype(str).str.match(_NODE_NAME_RE)
    match_ratio = matches.sum() / len(matches)
    if match_ratio < 0.8:
        return []

    # Parse into sub-columns (uppercase to match source convention)
    values = df[col].astype(str).str.upper()
    df["NODE_DEVICE_TYPE"] = values.str[:3]
    df["NODE_POOL"] = values.str[3:5]
    df["NODE_LOCATION"] = values.str[5:8]
    df["NODE_CUSTOMER_TYPE"] = values.str[8:11]

    # For rows where the original was NaN or didn't match, set sub-cols to NaN
    invalid = df[col].isna() | ~df[col].astype(str).str.match(_NODE_NAME_RE)
    for sub_col in ["NODE_DEVICE_TYPE", "NODE_POOL", "NODE_LOCATION", "NODE_CUSTOMER_TYPE"]:
        df.loc[invalid, sub_col] = None

    # Build ColumnInfo dicts for each new dimension
    new_dims = []
    for sub_col in ["NODE_DEVICE_TYPE", "NODE_POOL", "NODE_LOCATION", "NODE_CUSTOMER_TYPE"]:
        new_dims.append(_build_column_info(df, sub_col))

    return new_dims
