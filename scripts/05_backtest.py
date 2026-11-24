"""Bước 5: backtest long-only có ràng buộc VN cho một run → experiments/<run>/backtest.parquet"""

from pathlib import Path

from _common import setup

from vnqml.backtest import run_backtest
from vnqml.evaluation.metrics import portfolio_summary
from vnqml.utils.io import load_parquet, save_json, save_parquet


def extra(p):
    p.add_argument("--run", help="thư mục experiments/<run>; mặc định run mới nhất")


args, cfg, log = setup(__doc__, extra)
run = Path(args.run) if args.run else sorted(Path(cfg["project"]["run_dir"]).glob("*_*"))[-1]
signals = load_parquet(run / "predictions.parquet")
panel = load_parquet(f"{cfg['paths']['interim']}/panel.parquet")
bt = run_backtest(signals, panel, cfg)
save_parquet(bt, run / "backtest.parquet")
s = portfolio_summary(bt["net"], bt["turnover"])
save_json(s, run / "metrics_portfolio.json")
log.info("%s", s)
