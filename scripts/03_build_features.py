"""Bước 3: feature + nhãn, chỉ giữ dòng trong universe → data/processed/dataset.parquet"""

from _common import setup

from vnqml.features.build import build_features
from vnqml.labels.forward_returns import make_label
from vnqml.utils.io import load_parquet, save_parquet

args, cfg, log = setup(__doc__)
p = load_parquet(f"{cfg['paths']['interim']}/panel.parquet")
X = build_features(p, cfg)
y = make_label(p, cfg)
ds = X.join(y)[p["in_universe"]]
save_parquet(ds, f"{cfg['paths']['processed']}/dataset.parquet")
log.info("dataset: %s, %d feature", ds.shape, X.shape[1])
