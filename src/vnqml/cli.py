"""Entry point `vnqml <step> --config ...`, gọi lại các script trong scripts/."""

from __future__ import annotations

import argparse
import runpy
from pathlib import Path

STEPS = {
    "download": "01_download_data.py",
    "dataset": "02_build_dataset.py",
    "features": "03_build_features.py",
    "train": "04_train_walkforward.py",
    "backtest": "05_backtest.py",
    "report": "06_make_report.py",
    "signal": "07_daily_signal.py",
}


def main() -> None:
    p = argparse.ArgumentParser(prog="vnqml")
    p.add_argument("step", choices=STEPS)
    p.add_argument("--config", default="configs/base.yaml")
    a, rest = p.parse_known_args()
    script = Path("scripts") / STEPS[a.step]
    import sys

    sys.argv = [str(script), "--config", a.config, *rest]
    runpy.run_path(str(script), run_name="__main__")
