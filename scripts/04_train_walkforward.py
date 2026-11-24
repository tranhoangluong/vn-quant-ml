"""Bước 4: walk-forward train + conformal → experiments/<run>/predictions.parquet"""

from _common import setup

from vnqml.evaluation.metrics import coverage, ic_series, ic_summary
from vnqml.evaluation.walkforward import run_walkforward
from vnqml.utils.io import load_parquet, new_run_dir, save_json, save_parquet

args, cfg, log = setup(__doc__)
ds = load_parquet(f"{cfg['paths']['processed']}/dataset.parquet")
y = ds.pop("y")
run = new_run_dir(cfg)
preds = run_walkforward(ds, y, cfg, log=log.info)
save_parquet(preds, run / "predictions.parquet")
m = ic_summary(ic_series(preds["pred"], preds["y"]))
m["coverage"] = coverage(preds["y"].to_numpy(), preds["lo"].to_numpy(), preds["hi"].to_numpy())
save_json(m, run / "metrics_forecast.json")
log.info("%s → %s", m, run)
