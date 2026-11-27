"""Kho dữ liệu thô dạng parquet, chia theo ngày tải (snapshot) và theo mã.

    data/raw/
    ├── LATEST                                  # tên snapshot mới nhất, vd "2026-11-26"
    └── snapshot=2026-11-26/
        ├── _manifest.json                      # ngày tải, nguồn, phiên bản, số dòng, lỗi
        ├── listing.parquet                     # danh sách mã của VCI (có DELISTED)
        ├── prices/ticker=FPT/part-0.parquet    # date, open, high, low, close, volume
        ├── index/ticker=VN30/part-0.parquet    # chỉ số tham chiếu
        └── financials/
            ├── fields.parquet                  # mã chỉ tiêu → tên
            └── section=income_statement/ticker=FPT/part-0.parquet

Vì sao mỗi lần tải là một snapshot mới (không nối thêm vào file cũ): giá đã điều chỉnh
bị nguồn tính lại hồi tố sau mỗi lần chia cổ tức/phát hành, BCTC bị ghi đè khi điều
chỉnh. Giữ snapshot cũ giúp tái lập kết quả và đo được mức độ "sửa lịch sử" (`diff_snapshots`).
"""

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


# ---------- đường dẫn ----------
def snapshot_dir(raw: str | Path, snapshot: str | None = None) -> Path:
    """Thư mục của một snapshot. snapshot=None → snapshot mới nhất (file LATEST)."""
    raw = Path(raw)
    if snapshot is None:
        latest = raw / "LATEST"
        if not latest.exists():
            raise FileNotFoundError(f"Chưa có snapshot nào trong {raw}. Chạy `make data` trước.")
        snapshot = latest.read_text().strip()
    return raw / f"snapshot={snapshot}"


def part_path(snap: Path, dataset: str, ticker: str, section: str | None = None) -> Path:
    base = snap / dataset
    if section:
        base = base / f"section={section}"
    return base / f"ticker={ticker}" / "part-0.parquet"


# ---------- ghi ----------
def write_part(df: pd.DataFrame, path: Path, meta: dict, drop: tuple = ()) -> Path:
    """Ghi 1 file parquet, kèm metadata (nguồn, ngày tải...) ngay trong schema của file.

    Ghi ra file tạm rồi đổi tên để không bao giờ để lại file hỏng nếu bị ngắt giữa chừng.
    `drop`: cột phân vùng (vd "ticker") đã nằm trong tên thư mục nên bỏ khỏi dữ liệu.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df = df.drop(columns=list(drop), errors="ignore")
    table = pa.Table.from_pandas(df, preserve_index=False)
    md = dict(table.schema.metadata or {})
    md[b"vnqml"] = json.dumps(meta, ensure_ascii=False, default=str).encode()
    tmp = path.with_suffix(".tmp")
    pq.write_table(table.replace_schema_metadata(md), tmp, compression="zstd")
    tmp.replace(path)
    return path


def write_manifest(snap: Path, manifest: dict) -> None:
    (snap / "_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )


def set_latest(raw: str | Path, snapshot: str) -> None:
    Path(raw, "LATEST").write_text(snapshot + "\n")


def environment_info() -> dict:
    import numpy
    import requests

    from vnqml import __version__ as vnqml_version

    return {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "pyarrow": pa.__version__,
        "numpy": numpy.__version__,
        "requests": requests.__version__,
        "vnqml": vnqml_version,
        "git_commit": _git_commit(),
    }


def _git_commit() -> str | None:
    import subprocess

    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:  # noqa: BLE001
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------- đóng băng ----------
FROZEN = "_FROZEN"
CHECKSUMS = "_checksums.sha256"


def is_frozen(snap: Path) -> bool:
    return (Path(snap) / FROZEN).exists()


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def freeze(snap: Path, note: str = "") -> int:
    """Ghi checksum SHA-256 mọi file + đánh dấu _FROZEN. Trả về số file."""
    snap = Path(snap)
    files = sorted(p for p in snap.rglob("*") if p.is_file() and p.name not in (FROZEN, CHECKSUMS))
    lines = [f"{_sha256(p)}  {p.relative_to(snap).as_posix()}" for p in files]
    (snap / CHECKSUMS).write_text("\n".join(lines) + "\n")
    (snap / FROZEN).write_text(
        json.dumps({"frozen_at": utc_now(), "files": len(files), "note": note})
    )
    return len(files)


def verify(snap: Path) -> list[str]:
    """So checksum với lúc đóng băng. Trả về danh sách file bị đổi/thiếu/thêm (rỗng = nguyên vẹn)."""
    snap = Path(snap)
    want = {}
    for line in (snap / CHECKSUMS).read_text().splitlines():
        digest, rel = line.split("  ", 1)
        want[rel] = digest
    have = {
        p.relative_to(snap).as_posix(): p
        for p in snap.rglob("*")
        if p.is_file() and p.name not in (FROZEN, CHECKSUMS)
    }
    bad = [f"thiếu: {r}" for r in want if r not in have]
    bad += [f"thêm: {r}" for r in have if r not in want]
    bad += [f"đổi: {r}" for r in want if r in have and _sha256(have[r]) != want[r]]
    return bad


# ---------- đọc ----------
def read_dataset(
    raw: str | Path,
    dataset: str = "prices",
    snapshot: str | None = None,
    tickers: str | list[str] | None = None,
    section: str | None = None,
) -> pd.DataFrame:
    """Đọc cả một dataset (vd mọi mã trong prices/) thành 1 DataFrame có cột ticker.

    Ghép theo tên cột để giữ cả các chỉ tiêu BCTC chỉ xuất hiện ở một số mã.
    """
    base = snapshot_dir(raw, snapshot) / dataset
    if section:
        base = base / f"section={section}"
    parts = sorted(base.rglob("ticker=*/part-0.parquet"))
    if not parts:
        raise FileNotFoundError(f"Không tìm thấy part-0.parquet trong {base}")
    if isinstance(tickers, str):
        tickers = [tickers]
    wanted = set(tickers or ())
    selected = [p for p in parts if not wanted or p.parent.name.removeprefix("ticker=") in wanted]
    frames = []
    for path in selected or parts:
        if selected:
            frame = pd.read_parquet(path, partitioning=None)
        else:
            # Bộ lọc không khớp mã nào: trả bảng rỗng đủ cột, chỉ đọc schema.
            frame = pq.read_schema(path).empty_table().to_pandas()
        frame["ticker"] = path.parent.name.removeprefix("ticker=")
        if path.parent.parent != base:
            frame["section"] = path.parent.parent.name.removeprefix("section=")
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    sort = [
        c for c in ("ticker", "date", "period_type", "fiscal_year", "fiscal_quarter") if c in df
    ]
    return df.sort_values(sort).reset_index(drop=True)


def read_prices(raw: str | Path, snapshot: str | None = None, tickers=None) -> pd.DataFrame:
    """Giá dạng long: cột date, ticker, open, high, low, close, volume (đầu vào của bước 02)."""
    df = read_dataset(raw, "prices", snapshot, tickers)
    return df[["date", "ticker", "open", "high", "low", "close", "volume"]]


def read_meta(path: str | Path) -> dict:
    """Đọc metadata vnqml đã nhúng trong 1 file parquet."""
    md = pq.read_schema(path).metadata or {}
    return json.loads(md.get(b"vnqml", b"{}"))


def read_manifest(raw: str | Path, snapshot: str | None = None) -> dict:
    return json.loads((snapshot_dir(raw, snapshot) / "_manifest.json").read_text("utf-8"))


# ---------- kiểm tra ----------
def validate_prices(df: pd.DataFrame, max_gap_days: int = 15) -> pd.DataFrame:
    """Kiểm tra chất lượng giá, trả về bảng tóm tắt mỗi mã (không ném lỗi).

    - dup: số dòng trùng (date, ticker), phải = 0
    - bad_ohlc: high < max(open, close) hoặc low > min(open, close) hoặc giá <= 0
    - zero_vol: số phiên khối lượng 0 (ngừng giao dịch, hoặc lỗi)
    - big_moves: số phiên |lợi suất| > 7.5%, tức vượt biên độ HOSE. Không hẳn là lỗi:
      có thể là thời kỳ mã ở HNX (±10%) / UPCoM (±15%), ngày chào sàn, hoặc giá điều chỉnh sai
    - max_gap: khoảng trống dài nhất (ngày lịch) giữa 2 phiên; Tết thường 9-12 ngày, > max_gap_days là đáng xem
    """
    out = []
    for t, g in df.sort_values("date").groupby("ticker"):
        r = g["close"].pct_change()
        gaps = g["date"].diff().dt.days
        out.append(
            {
                "ticker": t,
                "rows": len(g),
                "first": g["date"].min().date(),
                "last": g["date"].max().date(),
                "dup": int(g["date"].duplicated().sum()),
                "bad_ohlc": int(
                    (
                        (g["high"] < g[["open", "close"]].max(axis=1))
                        | (g["low"] > g[["open", "close"]].min(axis=1))
                        | (g[["open", "high", "low", "close"]] <= 0).any(axis=1)
                    ).sum()
                ),
                "zero_vol": int((g["volume"] == 0).sum()),
                "big_moves": int((r.abs() > 0.075).sum()),
                "max_gap": int(gaps.max()) if len(g) > 1 else 0,
            }
        )
    rep = pd.DataFrame(out)
    rep["ok"] = (rep["dup"] == 0) & (rep["bad_ohlc"] == 0) & (rep["max_gap"] <= max_gap_days)
    return rep


def compare_sources(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    """So giá đóng cửa 2 nguồn cho 1 mã trên các ngày chung.

    Giá điều chỉnh của 2 nguồn có thể lệch nhau một hệ số (cách điều chỉnh khác nhau), nên
    quan trọng là lợi suất ngày có khớp không.
    """
    m = a[["date", "close"]].merge(b[["date", "close"]], on="date", suffixes=("_a", "_b"))
    ra, rb = m["close_a"].pct_change(), m["close_b"].pct_change()
    return {
        "common_days": len(m),
        "only_a": len(a) - len(m),
        "only_b": len(b) - len(m),
        "median_price_ratio": float((m["close_a"] / m["close_b"]).median()),
        "ret_corr": float(ra.corr(rb)),
        "ret_mismatch_days": int(((ra - rb).abs() > 0.005).sum()),  # lệch > 0.5 điểm %
    }


def diff_snapshots(raw: str | Path, old: str, new: str, tol: float = 1e-4) -> pd.DataFrame:
    """Đo mức "sửa lịch sử" giữa 2 snapshot: mỗi mã, bao nhiêu phiên có giá close đổi > tol."""
    a = read_prices(raw, old).set_index(["date", "ticker"])["close"]
    b = read_prices(raw, new).set_index(["date", "ticker"])["close"]
    j = pd.concat({"old": a, "new": b}, axis=1, join="inner")
    j["changed"] = (j["new"] / j["old"] - 1).abs() > tol
    return (
        j.groupby(level="ticker")
        .agg(common_days=("changed", "size"), changed_days=("changed", "sum"))
        .reset_index()
    )


def tidy_financials(df: pd.DataFrame, fields: pd.DataFrame | None = None) -> pd.DataFrame:
    """BCTC dạng rộng (cột isa1, bsa1...) → dạng dài: 1 dòng = (mã, kỳ, chỉ tiêu, giá trị)."""
    keys = [
        c
        for c in (
            "ticker",
            "period_type",
            "fiscal_year",
            "fiscal_quarter",
            "available_at",
            "available_at_conservative",
        )
        if c in df.columns
    ]
    value_cols = [c for c in df.columns if c[:3].isalpha() and c[3:].isdigit()]  # isa1, bsb12...
    long = df.melt(id_vars=keys, value_vars=value_cols, var_name="field", value_name="value")
    long = long.dropna(subset=["value"])
    if fields is not None:
        names = fields.drop_duplicates("field").set_index("field")["title_vi"]
        long["title_vi"] = long["field"].map(names)
    return long
