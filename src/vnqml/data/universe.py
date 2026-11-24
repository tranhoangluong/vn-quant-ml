"""Universe VN30 theo thời điểm (point-in-time).

Mỗi ngày giao dịch chỉ được phép chọn các mã thuộc VN30 *tại ngày đó*, theo file
`data/external/vn30_membership.csv` dạng snapshot (effective_date, ticker).
"""

from __future__ import annotations

import pandas as pd


def load_membership(path: str) -> pd.DataFrame:
    m = pd.read_csv(path, comment="#", parse_dates=["effective_date"])
    return m.sort_values("effective_date")


def membership_mask(index: pd.MultiIndex, membership: pd.DataFrame) -> pd.Series:
    """True nếu (date, ticker) thuộc rổ có hiệu lực gần nhất <= date."""
    snapshots = {d: set(g["ticker"]) for d, g in membership.groupby("effective_date")}
    eff_dates = pd.DatetimeIndex(sorted(snapshots))
    dates = index.get_level_values("date")
    pos = eff_dates.searchsorted(dates, side="right") - 1
    tickers = index.get_level_values("ticker")
    vals = [p >= 0 and t in snapshots[eff_dates[p]] for p, t in zip(pos, tickers)]
    return pd.Series(vals, index=index, name="in_universe")
