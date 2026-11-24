"""Bước 6: gom mọi run → bảng so sánh (LaTeX + CSV), DSR, PBO, hình → reports/ và thesis/"""

import json
from pathlib import Path

import pandas as pd
from _common import setup

from vnqml.evaluation.overfitting import deflated_sharpe, pbo_cscv
from vnqml.utils.io import load_parquet

args, cfg, log = setup(__doc__)
runs = sorted(Path(cfg["project"]["run_dir"]).glob("*_*"))
rows, rets = [], {}
for r in runs:
    if not (r / "backtest.parquet").exists():
        continue
    row = {"run": r.name}
    for f in ("metrics_forecast.json", "metrics_portfolio.json"):
        if (r / f).exists():
            row |= json.loads((r / f).read_text())
    rows.append(row)
    rets[r.name] = load_parquet(r / "backtest.parquet")["net"]
if not rows:
    raise SystemExit("Chưa có run nào có backtest.parquet")
tab = pd.DataFrame(rows).set_index("run")
R = pd.DataFrame(rets).dropna()
var_sr = (R.mean() / R.std()).var() if R.shape[1] > 1 else 0.0
tab["dsr"] = [deflated_sharpe(R[c], n_trials=R.shape[1], var_sr_trials=var_sr) for c in R]
if R.shape[1] >= 2:
    log.info("PBO = %.3f", pbo_cscv(R, cfg["evaluation"]["pbo_partitions"]))
out = Path(cfg["paths"]["reports"]) / "tables"
out.mkdir(parents=True, exist_ok=True)
tab.to_csv(out / "summary.csv")
tab.to_latex(Path("thesis/tables/summary.tex"), float_format="%.3f")
log.info("\n%s", tab)
