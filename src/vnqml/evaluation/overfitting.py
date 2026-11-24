"""Kiểm định chống overfitting backtest: Deflated Sharpe Ratio và PBO (CSCV).

Tham khảo: Bailey & López de Prado (2014) "The Deflated Sharpe Ratio";
Bailey, Borwein, López de Prado & Zhu (2017) "The Probability of Backtest Overfitting".
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from scipy import stats

EULER = 0.5772156649


def expected_max_sharpe(n_trials: int, var_sr: float) -> float:
    """Kỳ vọng Sharpe lớn nhất trong n_trials thử nghiệm độc lập dưới H0 (SR thực = 0)."""
    if n_trials <= 1:
        return 0.0
    z1 = stats.norm.ppf(1 - 1 / n_trials)
    z2 = stats.norm.ppf(1 - 1 / (n_trials * np.e))
    return float(np.sqrt(var_sr) * ((1 - EULER) * z1 + EULER * z2))


def deflated_sharpe(r: pd.Series, n_trials: int, var_sr_trials: float) -> float:
    """Xác suất SR thực > SR kỳ vọng tối đa do may mắn. Dùng SR theo tần suất của r (không annualize)."""
    r = r.dropna()
    t = len(r)
    sr = r.mean() / r.std(ddof=1)
    sr0 = expected_max_sharpe(n_trials, var_sr_trials)
    skew, kurt = stats.skew(r), stats.kurtosis(r, fisher=False)
    denom = np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr**2)
    return float(stats.norm.cdf((sr - sr0) * np.sqrt(t - 1) / denom))


def pbo_cscv(returns: pd.DataFrame, n_partitions: int = 16) -> float:
    """returns: T x N (mỗi cột là một cấu hình chiến lược). Trả về PBO trong [0, 1]."""
    m = returns.to_numpy()
    blocks = np.array_split(np.arange(len(m)), n_partitions)
    logits = []
    for combo in itertools.combinations(range(n_partitions), n_partitions // 2):
        is_idx = np.concatenate([blocks[i] for i in combo])
        oos_idx = np.concatenate([blocks[i] for i in range(n_partitions) if i not in combo])
        sr_is = m[is_idx].mean(0) / (m[is_idx].std(0) + 1e-12)
        sr_oos = m[oos_idx].mean(0) / (m[oos_idx].std(0) + 1e-12)
        best = int(np.argmax(sr_is))
        rank = stats.rankdata(sr_oos)[best] / (len(sr_oos) + 1)
        logits.append(np.log(rank / (1 - rank)))
    return float(np.mean(np.array(logits) <= 0))
