"""Đóng băng một snapshot: ghi checksum SHA-256 mọi file, chặn ghi thêm, tuỳ chọn nén zip.

python scripts/freeze_snapshot.py --snapshot 2026-11-26 --zip
python scripts/freeze_snapshot.py --snapshot 2026-11-26 --verify   # kiểm tra còn nguyên vẹn
"""

import shutil

from _common import setup

from vnqml.data import store


def extra(p):
    p.add_argument("--snapshot", required=True)
    p.add_argument(
        "--note", default="", help="ghi chú, vd 'snapshot nghiên cứu chính của luận văn'"
    )
    p.add_argument(
        "--zip", action="store_true", help="nén thành data/raw/snapshot=<ngày>.zip để sao lưu"
    )
    p.add_argument("--verify", action="store_true")


args, cfg, log = setup(__doc__, extra)
snap = store.snapshot_dir(cfg["paths"]["raw"], args.snapshot)
if not snap.exists():
    raise SystemExit(f"Không thấy {snap}")

if args.verify:
    bad = store.verify(snap)
    print("Nguyên vẹn." if not bad else "\n".join(bad))
    raise SystemExit(1 if bad else 0)

if store.is_frozen(snap):
    raise SystemExit(f"{snap.name} đã đóng băng rồi. Dùng --verify để kiểm tra.")
man = store.read_manifest(cfg["paths"]["raw"], args.snapshot)
if man.get("failures"):
    log.warning("Snapshot còn lỗi tải: %s", {k: len(v) for k, v in man["failures"].items()})
n = store.freeze(snap, args.note)
log.info("Đã đóng băng %s: %d file, checksum ở %s", snap.name, n, store.CHECKSUMS)
if args.zip:
    out = shutil.make_archive(str(snap), "zip", root_dir=snap.parent, base_dir=snap.name)
    log.info("Bản sao lưu: %s (cất lên Google Drive/ổ ngoài, KHÔNG commit lên GitHub)", out)
log.info('Ghim trong configs/base.yaml: data.snapshot: "%s"', args.snapshot)
