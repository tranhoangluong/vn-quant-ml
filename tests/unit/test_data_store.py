"""Test offline cho tải/lưu dữ liệu: parse phản hồi VCI và vòng ghi → đọc parquet."""

import pandas as pd
import pytest

from vnqml.data import store
from vnqml.data.sources import parse_vci_financials, parse_vci_ohlc

# Rút gọn từ phản hồi thật của gap-chart (FPT, 11/2026)
VCI_OHLC = {
    "symbol": "FPT",
    "o": [46950, 45600, 44900],
    "h": [47950, 46000, 47150],
    "l": [45600, 44650, 44050],
    "c": [45700, 45000, 46850],
    "v": [18437700, 15670800, 16985400],
    "t": ["1795046400", "1795132800", "1795392000"],
}


def test_parse_vci_ohlc_dates_and_types():
    df = parse_vci_ohlc(VCI_OHLC, pd.Timestamp("2026-01-01"), pd.Timestamp("2026-12-31"))
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert df["date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-11-19", "2026-11-20", "2026-11-23"]
    assert df["close"].dtype == "float64" and df["volume"].dtype == "int64"
    cut = parse_vci_ohlc(VCI_OHLC, pd.Timestamp("2026-11-20"), pd.Timestamp("2026-11-20"))
    assert len(cut) == 1


def test_parse_vci_financials_available_at():
    data = {
        "years": [
            {
                "organCode": "X",
                "ticker": "X",
                "yearReport": 2025,
                "lengthReport": 5,
                "publicDate": "2026-03-20T00:00:00",
                "createDate": "2026-01-27T11:31:11",
                "updateDate": "2026-03-20T11:31:15",
                "isa1": 1.0,
            }
        ],
        "quarters": [
            {
                "organCode": "X",
                "ticker": "X",
                "yearReport": 2026,
                "lengthReport": 3,
                "publicDate": None,
                "createDate": "2026-10-29T07:50:10",
                "updateDate": "2026-10-29T09:00:00",
                "isa1": 2.0,
            }
        ],
    }
    df = parse_vci_financials(data, "X")
    assert set(df["period_type"]) == {"year", "quarter"}
    q = df[df["period_type"] == "quarter"].iloc[0]
    assert q["available_at"] == pd.Timestamp("2026-10-29")  # thiếu publicDate → createDate


def test_parse_vci_financials_available_at_conservative():
    rows = [
        {"publicDate": "2026-03-20T09:00:00", "updateDate": "2026-05-04T18:30:00"},
        {"publicDate": "2026-03-20T09:00:00", "updateDate": "2026-01-27T11:00:00"},
        {"publicDate": "2026-03-20T09:00:00"},
        {"updateDate": "2026-05-04T18:30:00"},
        {},
    ]
    for row in rows:
        row["createDate"] = "2026-01-27T11:00:00"
    df = parse_vci_financials({"quarters": rows}, "FPT")
    expected = pd.to_datetime(["2026-05-04", "2026-03-20", "2026-03-20", "2026-05-04", None])
    pd.testing.assert_index_equal(
        pd.DatetimeIndex(df["available_at_conservative"]), expected, check_names=False
    )
    assert df.loc[0, "available_at"] == pd.Timestamp("2026-03-20")
    assert df.loc[3, "available_at"] == pd.Timestamp("2026-01-27")


def test_read_financials_keeps_indicators_from_each_ticker(tmp_path):
    snap = store.snapshot_dir(tmp_path, "2026-01-02")
    for ticker, field, value in [("FPT", "bsa1", 100), ("VCB", "bsb1", 200)]:
        path = store.part_path(snap, "financials", ticker, "balance_sheet")
        store.write_part(pd.DataFrame({field: [value]}), path, {})

    df = store.read_dataset(tmp_path, "financials", "2026-01-02", section="balance_sheet")
    by_ticker = df.set_index("ticker")
    assert by_ticker.loc["FPT", "bsa1"] == 100
    assert by_ticker.loc["VCB", "bsb1"] == 200
    assert pd.isna(by_ticker.loc["FPT", "bsb1"])
    assert pd.isna(by_ticker.loc["VCB", "bsa1"])


@pytest.mark.parametrize(("tickers", "expected"), [(["BBB"], "BBB"), ("AAA", "AAA")])
def test_write_read_roundtrip(tmp_path, tickers, expected):
    snap = store.snapshot_dir(tmp_path, "2026-01-02")
    for t in ["AAA", "BBB"]:
        df = parse_vci_ohlc(VCI_OHLC, pd.Timestamp("2026-01-01"), pd.Timestamp("2026-12-31"))
        store.write_part(df, store.part_path(snap, "prices", t), {"snapshot": "2026-01-02"})
    store.set_latest(tmp_path, "2026-01-02")
    p = store.read_prices(tmp_path)  # snapshot=None → LATEST
    assert p.shape == (6, 7) and sorted(p["ticker"].unique()) == ["AAA", "BBB"]
    assert store.read_meta(store.part_path(snap, "prices", "AAA"))["snapshot"] == "2026-01-02"
    rep = store.validate_prices(p)
    assert rep["ok"].all() and (rep["dup"] == 0).all()
    filtered = store.read_prices(tmp_path, tickers=tickers)
    pd.testing.assert_frame_equal(filtered, p[p["ticker"] == expected].reset_index(drop=True))


def test_diff_snapshots_detects_revision(tmp_path):
    base = parse_vci_ohlc(VCI_OHLC, pd.Timestamp("2026-01-01"), pd.Timestamp("2026-12-31"))
    revised = base.copy()
    revised.loc[0, "close"] *= 0.9  # nguồn điều chỉnh lại giá quá khứ
    for name, df in [("2026-01-01", base), ("2026-02-01", revised)]:
        store.write_part(
            df, store.part_path(store.snapshot_dir(tmp_path, name), "prices", "AAA"), {}
        )
    d = store.diff_snapshots(tmp_path, "2026-01-01", "2026-02-01")
    assert d.loc[0, "changed_days"] == 1


def test_freeze_and_verify(tmp_path):
    snap = store.snapshot_dir(tmp_path, "2026-01-01")
    df = parse_vci_ohlc(VCI_OHLC, pd.Timestamp("2026-01-01"), pd.Timestamp("2026-12-31"))
    path = store.write_part(df, store.part_path(snap, "prices", "AAA"), {})
    assert store.freeze(snap) == 1 and store.is_frozen(snap)
    assert store.verify(snap) == []
    path.write_bytes(b"hong")  # file bị sửa sau khi đóng băng
    assert store.verify(snap) == ["đổi: prices/ticker=AAA/part-0.parquet"]
