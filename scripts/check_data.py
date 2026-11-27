"""Kiểm tra snapshot dữ liệu thô: manifest, chất lượng giá, BCTC, kiểm chéo KBS.

python scripts/check_data.py                    # snapshot mới nhất
python scripts/check_data.py --snapshot 2026-11-26 --crosscheck FPT,VNM
python scripts/check_data.py --diff 2026-11-26  # so với một snapshot cũ
"""

import pandas as pd
from _common import setup

from vnqml.data import store
from vnqml.data.sources import KBS, SourceError
from vnqml.data.universe import load_membership


def extra(p):
    p.add_argument("--snapshot")
    p.add_argument("--crosscheck", help="mã để so giá VCI với KBS, vd FPT,VNM")
    p.add_argument("--diff", help="snapshot cũ để đo mức sửa lịch sử")


args, cfg, log = setup(__doc__, extra)
raw = cfg["paths"]["raw"]
pd.set_option("display.width", 160, "display.max_columns", 20)

man = store.read_manifest(raw, args.snapshot)
snap = man["snapshot"]
print(f"Snapshot {snap}  (tạo {man['created_at']}, cập nhật {man['updated_at']})")
print("Môi trường:", man["environment"])
print("Lỗi khi tải:", {k: list(v) for k, v in man["failures"].items()} or "không")

prices = store.read_prices(raw, snap)
print(f"\n[prices] {len(prices):,} dòng, {prices['ticker'].nunique()} mã")
rep = store.validate_prices(prices)
rep["board"] = rep["ticker"].map(man["ticker_board"])
print(rep.to_string(index=False) if len(rep) <= 60 else rep.describe().T.to_string())
bad = rep[~rep["ok"]]
if len(bad):
    print(
        f"\nCẦN XEM {len(bad)} mã (trùng ngày, OHLC sai, hoặc khoảng trống > 15 ngày):",
        bad["ticker"].tolist()[:30],
        "..." if len(bad) > 30 else "",
    )

# Mã trong vn30_membership.csv mà snapshot không có giá → survivorship bias, cần bổ sung tay
members = set(load_membership(cfg["data"]["membership_file"])["ticker"])
if members:
    missing = sorted(members - set(prices["ticker"]))
    print(
        f"\nMã VN30 thiếu giá: {missing or 'không'} "
        "(thường là mã sáp nhập/đổi mã hoặc huỷ niêm trước ~2022; lấy bù từ CafeF)"
    )

fin_root = store.snapshot_dir(raw, snap) / "financials"
if fin_root.exists():
    for sec in sorted(p.name.split("=")[1] for p in fin_root.glob("section=*")):
        f = store.read_dataset(raw, "financials", snap, section=sec)
        q = f[(f["period_type"] == "quarter") & f["fiscal_quarter"].between(1, 4)]
        qend = pd.PeriodIndex.from_fields(
            year=q["fiscal_year"], quarter=q["fiscal_quarter"], freq="Q"
        ).end_time.normalize()
        lag = (q["available_at"].values - qend.values).astype("timedelta64[D]").astype(int)
        print(
            f"[financials/{sec}] {len(f)} kỳ, {f['ticker'].nunique()} mã, "
            f"năm sớm nhất {int(f['fiscal_year'].min())}, "
            f"thiếu ngày công bố {int(f['public_date'].isna().sum())}, "
            f"trễ công bố BCTC quý: trung vị {pd.Series(lag).median():.0f} ngày, "
            f"lớn nhất {pd.Series(lag).max()} ngày"
        )

if args.crosscheck:
    kbs = KBS()
    for t in args.crosscheck.split(","):
        a = prices[prices["ticker"] == t]
        try:
            b = kbs.ohlcv(t, str(a["date"].min().date()), str(a["date"].max().date()))
        except SourceError as e:
            print(f"[crosscheck] {t}: {e}")
            continue
        print(f"[crosscheck VCI vs KBS] {t}:", store.compare_sources(a, b))

if args.diff:
    d = store.diff_snapshots(raw, args.diff, snap)
    print(f"\n[diff {args.diff} → {snap}] số phiên có giá close bị sửa:")
    print(d[d["changed_days"] > 0].to_string(index=False) or "không có")
