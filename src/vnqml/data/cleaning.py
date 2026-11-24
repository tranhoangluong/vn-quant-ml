"""Làm sạch giá: điều chỉnh, loại phiên lỗi, đánh dấu phiên chạm trần/sàn."""

from __future__ import annotations

import numpy as np
import pandas as pd


def basic_clean(panel: pd.DataFrame) -> pd.DataFrame:
    p = panel.copy()
    p = p[~p.index.duplicated(keep="last")]
    p = p[(p["close"] > 0) & (p["volume"] >= 0)]
    return p.sort_index()


def add_returns(panel: pd.DataFrame) -> pd.DataFrame:
    p = panel.copy()
    g = p.groupby(level="ticker")
    p["ret"] = g["close"].pct_change()
    p["prev_close"] = g["close"].shift(1)
    return p


def flag_price_limits(panel: pd.DataFrame, limit: float | None, tol: float = 0.002) -> pd.DataFrame:
    """limit_up/limit_down: phiên đóng cửa sát trần/sàn → khó mua/bán thực tế.

    Ghi chú: tick size làm giá trần thực tế thấp hơn prev_close*(1+limit) một chút,
    nên dùng sai số `tol`.
    """
    p = panel.copy()
    if limit is None:
        p["limit_up"] = False
        p["limit_down"] = False
        return p
    r = p["close"] / p["prev_close"] - 1
    p["limit_up"] = (r >= limit - tol).fillna(False)
    p["limit_down"] = (r <= -limit + tol).fillna(False)
    return p


def winsorize_cs(s: pd.Series, q: float = 0.01) -> pd.Series:
    """Cắt đuôi theo tiết diện từng ngày."""

    def _w(x: pd.Series) -> pd.Series:
        lo, hi = np.nanquantile(x, [q, 1 - q]) if x.notna().any() else (np.nan, np.nan)
        return x.clip(lo, hi)

    return s.groupby(level="date", group_keys=False).apply(_w)
