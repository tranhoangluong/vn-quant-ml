"""Chuyển dữ liệu giá về dạng panel chuẩn, hoặc đọc giá từ thư mục CSV.

Tải dữ liệu từ nguồn: xem `vnqml.data.sources` (VCI/KBS) và `vnqml.data.store` (parquet).
Đầu ra chuẩn (long format): index = (date, ticker), cột = open, high, low, close, volume.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

OHLCV = ["open", "high", "low", "close", "volume"]


def load_csv_dir(directory: str | Path) -> pd.DataFrame:
    """Đọc mỗi file <TICKER>.csv (cột date,open,high,low,close,volume) trong thư mục."""
    frames = []
    for f in sorted(Path(directory).glob("*.csv")):
        df = pd.read_csv(f, parse_dates=["date"])
        df["ticker"] = f.stem.upper()
        frames.append(df)
    return to_panel(pd.concat(frames, ignore_index=True))


def to_panel(df: pd.DataFrame) -> pd.DataFrame:
    return df.set_index(["date", "ticker"]).sort_index()[OHLCV]
