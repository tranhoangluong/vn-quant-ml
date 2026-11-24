import numpy as np
import pandas as pd

from vnqml.evaluation.overfitting import deflated_sharpe, pbo_cscv


def test_pbo_high_for_pure_noise():
    rng = np.random.default_rng(0)
    R = pd.DataFrame(rng.normal(0, 0.01, (1000, 20)))
    assert pbo_cscv(R, 8) > 0.3


def test_dsr_penalises_many_trials():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.001, 0.01, 1000))
    assert deflated_sharpe(r, 1, 0.0) > deflated_sharpe(r, 100, 0.002)
