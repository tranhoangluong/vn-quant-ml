import numpy as np
import pandas as pd

from vnqml.evaluation.metrics import coverage
from vnqml.uncertainty import get_calibrator


def _toy(n_days=400, n=30, shift=False, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.MultiIndex.from_product(
        [pd.bdate_range("2020-01-01", periods=n_days), range(n)], names=["date", "ticker"]
    )
    scale = (
        np.repeat(np.where(np.arange(n_days) > n_days // 2, 3.0, 1.0) if shift else 1.0, n)
        if shift
        else 1.0
    )
    y = rng.normal(0, 1, len(idx)) * scale
    return pd.Series(y, index=idx), np.zeros(len(idx))


def test_split_conformal_coverage():
    rng = np.random.default_rng(1)
    cal = get_calibrator({"method": "split", "alpha": 0.1}).fit(
        rng.normal(0, 1, 2000), np.zeros(2000)
    )
    y, pred = _toy()
    lo, hi = cal.predict_online(y, pred)
    assert abs(coverage(y.to_numpy(), lo, hi) - 0.9) < 0.02


def test_aci_recovers_coverage_under_shift():
    rng = np.random.default_rng(1)
    y, pred = _toy(shift=True)
    split = get_calibrator({"method": "split", "alpha": 0.1}).fit(
        rng.normal(0, 1, 2000), np.zeros(2000)
    )
    aci = get_calibrator({"method": "aci", "alpha": 0.1, "gamma": 0.02}).fit(
        rng.normal(0, 1, 2000), np.zeros(2000)
    )
    c_split = coverage(y.to_numpy(), *split.predict_online(y, pred))
    c_aci = coverage(y.to_numpy(), *aci.predict_online(y, pred, horizon=5))
    assert abs(c_aci - 0.9) < abs(c_split - 0.9)
