"""Backtest ngày, long-only, tín hiệu tại close t → khớp lệnh tại close t+1.

Đơn giản hoá (ghi rõ trong luận văn): khớp tại close t+1 thay vì open t+1 / VWAP;
lot size bỏ qua vì dùng trọng số. TODO: thêm tuỳ chọn khớp open và slippage.
"""

from __future__ import annotations

import pandas as pd

from ..portfolio.constraints import apply_constraints
from ..portfolio.construction import target_weights
from ..portfolio.costs import trading_cost


def _rebalance_days(dates: pd.DatetimeIndex, freq: str) -> set[pd.Timestamp]:
    if freq == "daily":
        return set(dates)
    s = pd.Series(dates, index=dates)
    return set(s.groupby(s.dt.to_period("W")).max())  # phiên cuối mỗi tuần


def run_backtest(signals: pd.DataFrame, panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """signals: index (date, ticker), cột pred/lo/hi. panel: có ret, limit_up, limit_down."""
    mcfg, pcfg = cfg["market"], cfg["portfolio"]
    dates = signals.index.get_level_values("date").unique().sort_values()
    rebal = _rebalance_days(dates, pcfg["rebalance"])
    rets = panel["ret"].unstack("ticker")
    lu = panel["limit_up"].unstack("ticker").fillna(False)
    ld = panel["limit_down"].unstack("ticker").fillna(False)
    w = pd.Series(dtype=float)
    bought_on: dict[str, int] = {}
    pending: pd.Series | None = None
    rows = []
    for i, d in enumerate(dates):
        # 1) danh mục đang giữ hưởng lợi suất close(d-1) → close(d)
        r = float((w * rets.loc[d].reindex(w.index).fillna(0)).sum()) if len(w) else 0.0
        if len(w):  # trôi trọng số theo giá
            w = (1 + rets.loc[d].reindex(w.index).fillna(0)) * w / (1 + r)
        # 2) khớp lệnh tại close(d) cho tín hiệu của phiên trước (chặn mã trần/sàn, T+2)
        cost, turnover = 0.0, 0.0
        if pending is not None:
            locked = {t for t, j in bought_on.items() if i - j < mcfg["settlement_days"]}
            new = apply_constraints(w, pending, lu.loc[d], ld.loc[d], locked)
            cost = trading_cost(w, new, mcfg)
            idx = w.index.union(new.index)
            turnover = float(
                (new.reindex(idx, fill_value=0) - w.reindex(idx, fill_value=0)).abs().sum()
            )
            for t in new.index:
                if new[t] > w.get(t, 0):
                    bought_on[t] = i
            w, pending = new, None
        rows.append(
            {
                "date": d,
                "gross": r,
                "cost": cost,
                "net": r - cost,
                "turnover": turnover,
                "n_pos": len(w),
            }
        )
        # 3) tín hiệu tại close(d) → lệnh cho phiên sau
        if d in rebal:
            pending = target_weights(signals.xs(d, level="date"), pcfg)
    return pd.DataFrame(rows).set_index("date")
