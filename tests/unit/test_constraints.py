import pandas as pd

from vnqml.portfolio.constraints import apply_constraints


def test_cannot_buy_limit_up_or_sell_locked():
    cur = pd.Series({"A": 0.5, "B": 0.5})
    tgt = pd.Series({"A": 0.0, "C": 0.5, "D": 0.5})
    lu = pd.Series({"C": True})
    ld = pd.Series(dtype=bool)
    new = apply_constraints(cur, tgt, lu, ld, locked={"A"})
    assert new.get("A") == 0.5  # T+2: chưa bán được
    assert "C" not in new  # tăng trần: không mua được
    assert new.sum() <= 1 + 1e-9
    assert (new >= 0).all()
