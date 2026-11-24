"""Bước 1: tải OHLCV của mọi mã từng thuộc VN30 + chỉ số → data/raw/prices.parquet"""

import time

import pandas as pd
from _common import setup

from vnqml.data.loaders import fetch_vnstock
from vnqml.data.universe import load_membership
from vnqml.utils.io import save_parquet

args, cfg, log = setup(__doc__, lambda p: p.add_argument("--incremental", action="store_true"))
dc = cfg["data"]
tickers = sorted(load_membership(dc["membership_file"])["ticker"].unique())
log.info("Tải %d mã (gồm cả mã đã rời rổ, tránh survivorship bias)", len(tickers))
frames = []
for t in tickers:
    try:
        frames.append(fetch_vnstock(t, dc["start"], dc["end"], dc["vnstock_source"]))
    except Exception as e:  # noqa: BLE001
        log.warning("Lỗi %s: %s", t, e)
    time.sleep(1.0)  # tôn trọng rate limit của nguồn miễn phí
df = pd.concat(frames, ignore_index=True)
save_parquet(df, f"{cfg['paths']['raw']}/prices.parquet")
log.info("Xong: %d dòng", len(df))
