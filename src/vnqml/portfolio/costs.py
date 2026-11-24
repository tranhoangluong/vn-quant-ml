import pandas as pd


def trading_cost(prev: pd.Series, new: pd.Series, mcfg: dict) -> float:
    idx = prev.index.union(new.index)
    d = new.reindex(idx, fill_value=0) - prev.reindex(idx, fill_value=0)
    buy, sell = d.clip(lower=0).sum(), (-d).clip(lower=0).sum()
    return float(buy * mcfg["fee_buy"] + sell * (mcfg["fee_sell"] + mcfg["tax_sell"]))
