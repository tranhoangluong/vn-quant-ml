"""Bước 2: làm sạch, tính lợi suất, cờ trần/sàn, mask universe → data/interim/panel.parquet"""

from _common import setup

from vnqml.data.cleaning import add_returns, basic_clean, flag_price_limits
from vnqml.data.loaders import to_panel
from vnqml.data.universe import load_membership, membership_mask
from vnqml.utils.io import load_parquet, save_parquet

args, cfg, log = setup(__doc__)
p = to_panel(load_parquet(f"{cfg['paths']['raw']}/prices.parquet").reset_index(drop=True))
p = flag_price_limits(add_returns(basic_clean(p)), cfg["market"]["price_limit"])
p["in_universe"] = membership_mask(p.index, load_membership(cfg["data"]["membership_file"]))
save_parquet(p, f"{cfg['paths']['interim']}/panel.parquet")
log.info("panel: %s, tỷ lệ in_universe=%.2f", p.shape, p["in_universe"].mean())
