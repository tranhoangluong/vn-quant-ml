import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vnqml.config import load_config  # noqa: E402
from vnqml.utils.logging import get_logger  # noqa: E402
from vnqml.utils.seed import set_seed  # noqa: E402


def setup(desc: str, extra=None):
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("--config", default="configs/base.yaml")
    if extra:
        extra(p)
    args = p.parse_args()
    cfg = load_config(args.config)
    set_seed(cfg["project"]["seed"])
    return args, cfg, get_logger(Path(sys.argv[0]).stem)
