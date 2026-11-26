"""Bước 2: làm sạch, tính lợi suất, cờ trần/sàn, mask universe → data/interim/panel.parquet

Đọc giá từ snapshot `data.snapshot` trong config (null = snapshot mới nhất, file data/raw/LATEST).
"""

from _common import setup

from vnqml.data import store
from vnqml.data.cleaning import add_returns, basic_clean, flag_price_limits
from vnqml.data.loaders import to_panel
from vnqml.data.universe import load_membership, membership_mask
from vnqml.utils.io import save_parquet

args, cfg, log = setup(__doc__)
snapshot = cfg["data"].get("snapshot")
log.info("Dùng snapshot dữ liệu: %s", store.snapshot_dir(cfg["paths"]["raw"], snapshot).name)
p = to_panel(store.read_prices(cfg["paths"]["raw"], snapshot))
p = flag_price_limits(add_returns(basic_clean(p)), cfg["market"]["price_limit"])
p["in_universe"] = membership_mask(p.index, load_membership(cfg["data"]["membership_file"]))
save_parquet(p, f"{cfg['paths']['interim']}/panel.parquet")
log.info("panel: %s, tỷ lệ in_universe=%.2f", p.shape, p["in_universe"].mean())
