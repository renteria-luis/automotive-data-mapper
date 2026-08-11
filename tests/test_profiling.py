# tests/test_profiling.py
import pandas as pd
from src.profiling import profile


def test_profile_counts_nulls_and_spare_spaces():
    df = pd.DataFrame({"a": ["x ", "y", None]})
    out = profile(df, ["a"])

    assert len(out) == 1
    assert out.loc[0, "nulls"] == 1
    assert out.loc[0, "unique"] == 2
    assert out.loc[0, "spare_spaces"] == 1