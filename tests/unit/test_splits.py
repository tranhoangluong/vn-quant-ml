import pandas as pd

from vnqml.evaluation.splits import walk_forward


def test_folds_are_ordered_and_embargoed(panel, cfg):
    dates = panel.index.get_level_values("date").unique()
    folds = walk_forward(dates, cfg)
    assert len(folds) >= 2
    for f in folds:
        assert f.train[1] < f.valid[0] < f.valid[1] < f.test[0]
        gap = ((dates > f.valid[1]) & (dates < f.test[0])).sum()
        assert gap >= cfg["split"]["embargo_days"]
    assert all(a.test[0] < b.test[0] for a, b in zip(folds, folds[1:]))
    assert folds[0].test[0] == pd.Timestamp(cfg["split"]["test_start"])
