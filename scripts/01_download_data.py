"""Bước 1: tải OHLCV + BCTC → data/raw/snapshot=<ngày>/

Chọn danh sách mã (một trong các cách):
    (mặc định)                     mọi mã trong data/external/vn30_membership.csv
    --tickers FPT,VNM,ROS          vài mã để thử
    --tickers-file mylist.txt      mỗi dòng một mã
    --universe all-stocks          MỌI cổ phiếu VCI biết: đang niêm yết HOSE/HNX/UPCoM và đã huỷ
                                   niêm yết (lọc bằng --boards). Dùng khi file VN30 còn trống:
                                   tập này chứa mọi mã từng vào VN30 mà VCI còn giữ dữ liệu.

Ví dụ snapshot nghiên cứu cố định:
    python scripts/01_download_data.py --universe all-stocks --start 2014-01-01 --end 2026-11-26
    python scripts/check_data.py
    python scripts/freeze_snapshot.py --snapshot 2026-11-26

Chạy lại cùng --snapshot sẽ bỏ qua các file đã có (resume); --force để tải lại.
Snapshot đã đóng băng (freeze) thì không ghi thêm được.
"""

from pathlib import Path

import pandas as pd
import requests
from _common import setup

from vnqml.data import store
from vnqml.data.sources import CLIENT_VERSION, FIN_SECTIONS, VCI, SourceError
from vnqml.data.universe import load_membership


def extra(p):
    p.add_argument("--tickers", help="danh sách mã, phân tách bằng dấu phẩy")
    p.add_argument("--tickers-file", help="file văn bản, mỗi dòng một mã")
    p.add_argument("--universe", choices=["membership", "all-stocks"], default="membership")
    p.add_argument(
        "--boards",
        default="HSX,HNX,UPCOM,DELISTED",
        help="với --universe all-stocks: sàn cần lấy (HSX,HNX,UPCOM,DELISTED)",
    )
    p.add_argument("--start", help="ghi đè data.start trong config, vd 2014-01-01")
    p.add_argument("--end", help="ghi đè data.end; nên cố định cho snapshot nghiên cứu")
    p.add_argument("--snapshot", help="tên snapshot (mặc định: hôm nay, YYYY-MM-DD)")
    p.add_argument("--no-financials", action="store_true")
    p.add_argument("--force", action="store_true", help="tải lại cả file đã có")
    p.add_argument("--incremental", action="store_true", help="(giữ cho workflow cũ, = resume)")


args, cfg, log = setup(__doc__, extra)
dc = cfg["data"]
raw = cfg["paths"]["raw"]

snapshot = args.snapshot or pd.Timestamp.today().strftime("%Y-%m-%d")
snap = store.snapshot_dir(raw, snapshot)
if store.is_frozen(snap):
    raise SystemExit(f"Snapshot {snapshot} đã đóng băng, không ghi thêm. Dùng --snapshot khác.")
src = VCI(min_interval=dc.get("min_interval_sec", 1.0))

# 1) Danh sách mã của VCI: biết mã nào đã huỷ niêm yết (board == DELISTED)
lst = src.listing()
status = lst.set_index("symbol")["board"].to_dict()

if args.tickers:
    tickers = {t.strip().upper() for t in args.tickers.split(",")}
elif args.tickers_file:
    lines = Path(args.tickers_file).read_text().splitlines()
    tickers = {t.strip().upper() for t in lines if not t.strip().startswith("#")}
elif args.universe == "all-stocks":
    boards = [b.strip().upper() for b in args.boards.split(",")]
    sel = lst[(lst["type"] == "STOCK") & lst["board"].isin(boards)]
    tickers = set(sel["symbol"])
    log.info("all-stocks: %s", sel["board"].value_counts().to_dict())
else:
    tickers = set(load_membership(dc["membership_file"])["ticker"])
tickers = sorted(t for t in tickers if t)
if not tickers:
    raise SystemExit(
        "Chưa có mã nào: điền data/external/vn30_membership.csv, "
        "hoặc dùng --universe all-stocks / --tickers FPT,VNM"
    )

snap.mkdir(parents=True, exist_ok=True)
start = args.start or dc["start"]
end = args.end or dc["end"] or pd.Timestamp.today().strftime("%Y-%m-%d")
base_meta = {"snapshot": snapshot, "source": src.name, "client": CLIENT_VERSION}
log.info("Snapshot %s: %d mã, %s → %s, nguồn %s", snapshot, len(tickers), start, end, src.name)

counts, failures = {}, {}


def fetch_and_write(dataset, ticker, fn, section=None):
    path = store.part_path(snap, dataset, ticker, section)
    key = f"{dataset}/{section}" if section else dataset
    if path.exists() and not args.force:
        return  # đã có trong snapshot này
    try:
        df = fn()
    except (SourceError, requests.RequestException, ValueError) as e:
        failures.setdefault(key, {})[ticker] = str(e)
        log.warning("%s %s: %s", key, ticker, e)
        return
    meta = {**base_meta, "ticker": ticker, "fetched_at": store.utc_now(), "rows": len(df)}
    store.write_part(df, path, meta, drop=("ticker",))
    counts[key] = counts.get(key, 0) + 1
    log.info("%-28s %-5s %5d dòng", key, ticker, len(df))


if not (snap / "listing.parquet").exists() or args.force:
    store.write_part(lst, snap / "listing.parquet", {**base_meta, "fetched_at": store.utc_now()})
missing = [t for t in tickers if t not in status]
if missing:
    log.warning("Không có trong danh sách VCI (có thể đã sáp nhập/đổi mã): %s", missing)

# 2) Giá cổ phiếu + chỉ số tham chiếu
log.info("Ước tính thời gian: ~%.0f phút cho giá, gấp 3 lần nữa cho BCTC", len(tickers) * 1.2 / 60)
for i, t in enumerate(tickers, 1):
    if i % 100 == 0:
        log.info("... %d/%d mã", i, len(tickers))
    fetch_and_write("prices", t, lambda t=t: src.ohlcv(t, start, end))
for idx in dc.get("index_symbols", ["VN30", "VNINDEX"]):
    fetch_and_write("index", idx, lambda i=idx: src.ohlcv(i, start, end))

# 3) BCTC (VCI chỉ có từ khoảng 2018) + bảng tên chỉ tiêu
if not args.no_financials:
    # chỉ lấy BCTC cho mã có giá trong khoảng nghiên cứu (bỏ mã huỷ niêm trước start)
    with_prices = [t for t in tickers if store.part_path(snap, "prices", t).exists()]
    for t in with_prices:
        for sec in FIN_SECTIONS:
            fetch_and_write("financials", t, lambda t=t, s=sec: src.financials(t, s), section=sec)
    fpath = snap / "financials" / "fields.parquet"
    if not fpath.exists() or args.force:
        store.write_part(src.financial_fields(), fpath, base_meta)

# 4) Manifest: mọi thứ cần để ghi vào luận văn / tái lập.
# Chạy tiếp (resume) cùng snapshot thì gộp với manifest cũ, không ghi đè mất thông tin.
old = store.read_manifest(raw, snapshot) if (snap / "_manifest.json").exists() else {}
all_tickers = sorted(set(old.get("tickers", [])) | set(tickers))
for key, errs in old.get("failures", {}).items():
    # lỗi cũ còn giữ nếu lần này mã đó vẫn chưa có file
    dataset, _, section = key.partition("/")
    for t, e in errs.items():
        if not store.part_path(snap, dataset, t, section or None).exists():
            failures.setdefault(key, {}).setdefault(t, e)
manifest = {
    "snapshot": snapshot,
    "created_at": old.get("created_at", store.utc_now()),
    "updated_at": store.utc_now(),
    "source": {
        "name": "Vietcap (VCI) public web API",
        "prices": "POST https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart",
        "financials": "GET https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/{t}/financial-statement",
        "price_adjustment": "giá đã điều chỉnh theo sự kiện quyền, đơn vị VND",
    },
    "config": {"start": start, "end": end, "universe": args.universe, "boards": args.boards},
    "tickers": all_tickers,
    "ticker_board": {t: status.get(t) for t in all_tickers},
    "files_written_last_run": counts,
    "failures": {k: v for k, v in failures.items() if v},
    "environment": store.environment_info(),
}
store.write_manifest(snap, manifest)
store.set_latest(raw, snapshot)
log.info(
    "Xong snapshot %s. Ghi mới: %s. Lỗi: %s",
    snapshot,
    counts,
    {k: len(v) for k, v in failures.items()},
)
