# src/profiling.py
import pandas as pd


def profile(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Nulls, distinct values and spare surrounding spaces, one row per column."""
    rows = []
    for c in columns:
        s = df[c]
        row = {"column": c, "nulls": int(s.isna().sum()), "unique": int(s.nunique())}
        if s.dtype == "object":
            text = s.dropna().astype(str)
            row["spare_spaces"] = int((text != text.str.strip()).sum())
        else:
            row["spare_spaces"] = None
        rows.append(row)
    return pd.DataFrame(rows)