"""Vòng lặp walk-forward: train → valid (early stopping + calibration) → test."""

from __future__ import annotations

import pandas as pd

from ..models import get_model
from ..uncertainty import get_calibrator
from .splits import slice_dates, walk_forward


def run_walkforward(X: pd.DataFrame, y: pd.Series, cfg: dict, log=print) -> pd.DataFrame:
    data = X.join(y, how="inner").dropna(subset=[y.name])
    folds = walk_forward(data.index.get_level_values("date"), cfg)
    feats = list(X.columns)
    outs = []
    for f in folds:
        tr, va, te = (slice_dates(data, s) for s in (f.train, f.valid, f.test))
        model = get_model(cfg["model"]["name"], cfg["model"].get("params"))
        model.fit(tr[feats], tr[y.name], va[feats], va[y.name])
        cal = get_calibrator(cfg["uncertainty"])
        cal.fit(va[y.name].to_numpy(), model.predict(va[feats]))
        pred = model.predict(te[feats])
        lo, hi = cal.predict_online(te[y.name], pred, horizon=cfg["label"]["horizon"])
        outs.append(
            pd.DataFrame(
                {"pred": pred, "lo": lo, "hi": hi, "y": te[y.name], "fold": f.k}, index=te.index
            )
        )
        log(f"fold {f.k}: test {f.test[0]:%Y-%m-%d}..{f.test[1]:%Y-%m-%d}, n={len(te)}")
    return pd.concat(outs).sort_index()
