"""Tải giá OHLCV ngày. vnstock được import lười để test/CI chạy không cần mạng.

Đầu ra chuẩn (long format): index = (date, ticker), cột = open, high, low, close, volume.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

OHLCV = ["open", "high", "low", "close", "volume"]


def fetch_vnstock(ticker: str, start: str, end: str | None, source: str = "VCI") -> pd.DataFrame:
    from vnstock import Vnstock  # optional dependency: pip install -e ".[data]"

    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    df = (
        Vnstock()
        .stock(symbol=ticker, source=source)
        .quote.history(start=start, end=end, interval="1D")
    )
    df = df.rename(columns=str.lower).rename(columns={"time": "date"})
    df["date"] = pd.to_datetime(df["date"])
    df["ticker"] = ticker
    return df[["date", "ticker", *OHLCV]]


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
