import re

import pandas as pd


def _backtick_formula(formula: str, columns: list[str]) -> str:
    """Wrap column names in backticks so pandas.eval handles dots/spaces."""
    sorted_cols = sorted(columns, key=len, reverse=True)
    for col in sorted_cols:
        pattern = r'(?<![`\w.])' + re.escape(col) + r'(?![`\w.])'
        formula = re.sub(pattern, f'`{col}`', formula)
    return formula


def compute_kpis(df: pd.DataFrame, kpi_definitions: list[dict]) -> pd.DataFrame:
    """
    Add virtual KPI columns to a DataFrame using pandas eval.

    Must be called AFTER aggregation by dimensions — you cannot average a ratio.
    Each KPI formula references existing column names with standard math operators.

    Args:
        df: DataFrame with base metric columns (already aggregated).
        kpi_definitions: List of dicts with "name" and "formula" keys.

    Returns:
        The same DataFrame with KPI columns added.
    """
    for kpi in kpi_definitions:
        name = kpi["name"]
        formula = kpi["formula"]
        try:
            normalized = _normalize_formula(formula)
            backticked = _backtick_formula(normalized, list(df.columns))
            df[name] = df.eval(backticked)
        except Exception:
            # Graceful fallback: column exists but is all NaN
            df[name] = float("nan")
    return df


def get_kpi_source_columns(kpi_definitions: list[dict], available_columns: list[str]) -> list[str]:
    """
    Extract column names referenced in KPI formulas that exist in the dataset.
    Used to ensure we load the right columns from Parquet even if the user only
    selected the KPI (not its source columns) for analysis.
    """
    source_cols = set()
    for kpi in kpi_definitions:
        formula = kpi["formula"]
        for col in available_columns:
            if col in formula:
                source_cols.add(col)
    return list(source_cols)


def _extract_unknown_variables(formula: str, columns: list[str]) -> list[str]:
    """Find tokens in a formula that don't match any known column or builtin."""
    _builtins = {"abs", "min", "max", "sum", "mean", "sqrt", "log", "exp", "where", "and", "or", "not"}
    col_set = set(columns)

    # Match backtick-wrapped names and bare identifiers
    backticked = re.findall(r'`([^`]+)`', formula)
    bare = re.findall(r'(?<![`\w.])([A-Za-z_]\w*(?:\.\w+)*)(?![`\w.])', formula)

    unknown = []
    for name in backticked + bare:
        if name not in col_set and name not in _builtins:
            unknown.append(name)
    # Deduplicate while preserving order
    return list(dict.fromkeys(unknown))


def _friendly_formula_error(formula: str, columns: list[str], exc: Exception) -> str:
    """Turn opaque pandas.eval errors into actionable messages."""
    msg = str(exc)

    # "'BinOp' object has no attribute 'type'" or similar AST node errors
    # usually mean an unrecognised variable name.
    if "has no attribute 'type'" in msg or "UndefinedVariableError" in msg:
        unknown = _extract_unknown_variables(formula, columns)
        if unknown:
            return f"Unrecognised variable(s): {', '.join(unknown)}. Check column names or use the autocomplete suggestions."
        return "Formula contains an unrecognised variable. Check that all column names are correct."

    # pandas "unknown variable" message — extract the name
    if "is not defined" in msg:
        # e.g. "name 'foo' is not defined"
        m = re.search(r"name '([^']+)' is not defined", msg)
        if m:
            return f"Unrecognised variable: {m.group(1)}. This column does not exist in the dataset."
        return msg

    # Last resort: still try to identify unknown variables for any error
    unknown = _extract_unknown_variables(formula, columns)
    if unknown:
        return f"{msg} (possible unrecognised variable(s): {', '.join(unknown)})"

    return msg


def _normalize_formula(formula: str) -> str:
    """Collapse newlines and extra whitespace so pandas.eval can parse it."""
    return re.sub(r'\s+', ' ', formula).strip()


def validate_kpi(df: pd.DataFrame, formula: str) -> str | None:
    """
    Validate a KPI formula against a sample of real data.
    Returns None if valid, or an error message string.
    """
    try:
        sample = df.head(100).copy()
        normalized = _normalize_formula(formula)
        backticked = _backtick_formula(normalized, list(sample.columns))
        result = sample.eval(backticked)
        if result is None:
            return "Formula returned None"
        return None
    except Exception as e:
        return _friendly_formula_error(formula, list(df.columns), e)
