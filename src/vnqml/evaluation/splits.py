"""Walk-forward split theo thời gian, có embargo để chống rò rỉ nhãn chồng lấn.

Mỗi fold: [train][embargo][valid][embargo][test]; fold sau dịch đi `step_months`.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Fold:
    k: int
    train: tuple[pd.Timestamp, pd.Timestamp]
    valid: tuple[pd.Timestamp, pd.Timestamp]
    test: tuple[pd.Timestamp, pd.Timestamp]


def _shift_days(dates: pd.DatetimeIndex, d: pd.Timestamp, n: int) -> pd.Timestamp:
    i = min(max(dates.searchsorted(d) + n, 0), len(dates) - 1)
    return dates[i]


def walk_forward(dates: pd.DatetimeIndex, cfg: dict) -> list[Fold]:
    sc = cfg["split"]
    dates = pd.DatetimeIndex(sorted(set(dates)))
    emb = sc["embargo_days"]
    test_start = pd.Timestamp(sc["test_start"])
    folds, k = [], 0
    while True:
        test_end = test_start + pd.DateOffset(months=sc["test_months"]) - pd.Timedelta(days=1)
        if test_start > dates[-1]:
            break
        valid_end = _shift_days(dates, test_start, -emb - 1)
        valid_start = valid_end - pd.DateOffset(months=sc["valid_months"]) + pd.Timedelta(days=1)
        train_end = _shift_days(dates, valid_start, -emb - 1)
        if sc["scheme"] == "rolling":
            train_start = train_end - pd.DateOffset(years=sc["train_years"])
        else:
            train_start = dates[0]
        if train_start < dates[0] or (train_end - train_start).days < 365:
            test_start += pd.DateOffset(months=sc["step_months"])
            continue
        folds.append(
            Fold(
                k,
                (train_start, train_end),
                (valid_start, valid_end),
                (test_start, min(test_end, dates[-1])),
            )
        )
        k += 1
        test_start += pd.DateOffset(months=sc["step_months"])
    return folds


def slice_dates(df: pd.DataFrame, span: tuple[pd.Timestamp, pd.Timestamp]) -> pd.DataFrame:
    d = df.index.get_level_values("date")
    return df[(d >= span[0]) & (d <= span[1])]
