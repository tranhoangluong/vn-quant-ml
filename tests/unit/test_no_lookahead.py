"""Test quan trọng nhất của dự án: feature tại t không được dùng dữ liệu sau t."""

import numpy as np

from vnqml.features.build import build_features
from vnqml.labels.forward_returns import forward_return


def test_features_unchanged_when_future_is_altered(panel, cfg):
    cfg["features"]["cross_sectional_rank"] = False
    cut = panel.index.get_level_values("date").unique()[600]
    X1 = build_features(panel, cfg)
    p2 = panel.copy()
    future = p2.index.get_level_values("date") > cut
    p2.loc[future, ["open", "high", "low", "close"]] *= 3.0
    p2.loc[future, "ret"] = np.nan
    X2 = build_features(p2, cfg)
    past = X1.index.get_level_values("date") <= cut
    np.testing.assert_allclose(X1[past].to_numpy(), X2[past].to_numpy(), equal_nan=True)


def test_forward_return_is_strictly_future(panel):
    y = forward_return(panel, 5, "next_close")
    t = panel.xs("T00", level="ticker")["close"]
    yt = y.xs("T00", level="ticker")
    assert np.isclose(yt.iloc[0], t.iloc[6] / t.iloc[1] - 1)
