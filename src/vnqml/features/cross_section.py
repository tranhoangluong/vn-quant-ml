"""Chuẩn hoá theo tiết diện (mỗi ngày): rank về [-0.5, 0.5] hoặc z-score."""

import pandas as pd


def cs_rank(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(level="date").rank(pct=True) - 0.5


def cs_zscore(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(level="date")
    return (df - g.transform("mean")) / g.transform("std")
