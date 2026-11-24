"""Ràng buộc giao dịch thị trường VN áp lên lệnh mục tiêu.

- Biên độ giá: mã tăng trần ở phiên thực hiện → không mua thêm được; giảm sàn → không bán được.
- T+2: cổ phiếu mua ở phiên t chỉ bán được từ phiên t+settlement_days.
- Không bán khống: trọng số >= 0.
"""

from __future__ import annotations

import pandas as pd


def apply_constraints(
    current: pd.Series,
    target: pd.Series,
    limit_up: pd.Series,
    limit_down: pd.Series,
    locked: set[str],
) -> pd.Series:
    tickers = current.index.union(target.index)
    cur = current.reindex(tickers, fill_value=0.0)
    tgt = target.reindex(tickers, fill_value=0.0).clip(lower=0)
    up = limit_up.reindex(tickers, fill_value=False)
    dn = limit_down.reindex(tickers, fill_value=False)
    buy_blocked = (tgt > cur) & up
    sell_blocked = (tgt < cur) & (dn | tickers.isin(list(locked)))
    new = tgt.where(~(buy_blocked | sell_blocked), cur)
    if new.sum() > 1:  # không dùng margin: co phần mua mới cho vừa
        buys = (new - cur).clip(lower=0)
        room = 1 - new.where(buys == 0, cur).sum()
        new = new - buys + buys * max(room, 0) / buys.sum()
    return new[new > 1e-9]
