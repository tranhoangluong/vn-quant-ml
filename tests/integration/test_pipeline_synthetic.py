"""Chạy toàn bộ pipeline trên dữ liệu giả lập (không cần mạng)."""

from vnqml.backtest import run_backtest
from vnqml.evaluation.walkforward import run_walkforward
from vnqml.features.build import build_features
from vnqml.labels.forward_returns import make_label


def test_end_to_end(panel, cfg):
    cfg["model"]["params"]["n_estimators"] = 50
    cfg["split"]["test_start"] = "2019-01-01"
    X, y = build_features(panel, cfg), make_label(panel, cfg)
    preds = run_walkforward(X, y, cfg, log=lambda *_: None)
    assert {"pred", "lo", "hi"} <= set(preds.columns)
    bt = run_backtest(preds, panel, cfg)
    assert len(bt) > 100
    assert (bt["n_pos"] <= cfg["portfolio"]["top_k"]).all()
