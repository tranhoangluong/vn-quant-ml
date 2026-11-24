"""Feature từ giá/khối lượng. Mọi feature tại ngày t chỉ dùng thông tin <= t."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _by_ticker(panel: pd.DataFrame):
    return panel.groupby(level="ticker", group_keys=False)


def momentum(panel: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    out = {}
    for w in windows:
        out[f"mom_{w}"] = _by_ticker(panel)["close"].pct_change(w)
    if 252 in windows and 21 in windows:
        out["mom_12_1"] = (1 + out["mom_252"]) / (1 + out["mom_21"]) - 1
    return pd.DataFrame(out)


def volatility(panel: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    r = panel["ret"]
    g = r.groupby(level="ticker")
    return pd.DataFrame(
        {
            f"vol_{w}": g.transform(lambda x, w=w: x.rolling(w, min_periods=w // 2).std())
            for w in windows
        }
    )


def liquidity(panel: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    dv = panel["close"] * panel["volume"]
    absr = panel["ret"].abs()
    g_dv = dv.groupby(level="ticker")
    out = {}
    for w in windows:
        out[f"logdv_{w}"] = np.log1p(
            g_dv.transform(lambda x, w=w: x.rolling(w, min_periods=w // 2).mean())
        )
        amihud = (absr / dv.replace(0, np.nan)).groupby(level="ticker")
        out[f"amihud_{w}"] = amihud.transform(
            lambda x, w=w: x.rolling(w, min_periods=w // 2).mean()
        )
    return pd.DataFrame(out)


def reversal(panel: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {"rev_1": -panel["ret"], "rev_5": -_by_ticker(panel)["close"].pct_change(5)}
    )


def technical(panel: pd.DataFrame) -> pd.DataFrame:
    hl = (panel["high"] - panel["low"]) / panel["close"]
    co = panel["close"] / panel["open"] - 1
    return pd.DataFrame(
        {
            "hl_range": hl,
            "intraday_ret": co,
            "limit_up_flag": panel.get("limit_up", False).astype(float),
        }
    )
