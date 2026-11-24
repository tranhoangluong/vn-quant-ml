import numpy as np
import pandas as pd
import pytest

from vnqml.config import load_config


@pytest.fixture
def cfg():
    return load_config("configs/base.yaml")


@pytest.fixture
def panel():
    """Dữ liệu giả lập: 12 mã x ~6 năm, có tín hiệu momentum yếu để test end-to-end."""
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2014-01-01", "2020-06-30")
    tickers = [f"T{i:02d}" for i in range(12)]
    frames = []
    for j, t in enumerate(tickers):
        r = rng.normal(0.0002 * (j - 6), 0.018, len(dates)).clip(-0.069, 0.069)
        close = 10_000 * np.cumprod(1 + r)
        frames.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "ticker": t,
                    "open": close * (1 + rng.normal(0, 0.003, len(dates))),
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": rng.integers(1e5, 1e6, len(dates)),
                }
            )
        )
    from vnqml.data.cleaning import add_returns, basic_clean, flag_price_limits
    from vnqml.data.loaders import to_panel

    p = to_panel(pd.concat(frames))
    return flag_price_limits(add_returns(basic_clean(p)), 0.07)
