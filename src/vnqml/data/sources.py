"""Tải dữ liệu thô từ API công khai của Vietcap (VCI), kiểm chéo bằng KBS.

Vì sao không dùng thư viện vnstock: từ ~24/09/2026 PyPI cách ly (quarantine) gói `vnstock`
và `vnai`, và mọi bản trước "thế hệ 6" ngừng hoạt động từ 10/11/2026. Module này gọi thẳng
đúng các endpoint mà vnstock 3.x từng gọi, chỉ cần `requests`.

Lưu ý: đây là endpoint nội bộ của website, không phải API được công bố chính thức. Chúng có
thể đổi bất cứ lúc nào; hãy tôn trọng điều khoản sử dụng của nguồn và gọi chậm (mặc định
1 request/giây).

Đơn vị: giá theo VND (đồng), đã điều chỉnh theo sự kiện quyền; khối lượng theo cổ phiếu.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd

VCI_TRADING = "https://trading.vietcap.com.vn/api"
VCI_IQ = "https://iq.vietcap.com.vn/api/iq-insight-service/v1"
KBS_IIS = "https://kbbuddywts.kbsec.com.vn/iis-server/investment"

FIN_SECTIONS = {
    "balance_sheet": "BALANCE_SHEET",
    "income_statement": "INCOME_STATEMENT",
    "cash_flow": "CASH_FLOW",
}
OHLCV = ["open", "high", "low", "close", "volume"]
CLIENT_VERSION = "vnqml-sources/0.1"


class SourceError(RuntimeError):
    """Nguồn trả lỗi hoặc không có dữ liệu."""


@dataclass
class HttpClient:
    """requests.Session có giãn cách tối thiểu giữa 2 lần gọi và retry có backoff."""

    min_interval: float = 1.0  # giây giữa 2 request (rate limit nguồn miễn phí)
    timeout: float = 60.0
    retries: int = 3
    headers: dict = field(default_factory=dict)
    _last: float = 0.0

    def __post_init__(self):
        import requests  # import lười để test offline không cần mạng

        self._s = requests.Session()
        self._s.headers.update({"User-Agent": "Mozilla/5.0 (academic research)", **self.headers})

    def request(self, method: str, url: str, **kw):
        for attempt in range(self.retries + 1):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                r = self._s.request(method, url, timeout=self.timeout, **kw)
            except Exception as e:  # noqa: BLE001  (lỗi mạng: thử lại)
                err = e
            else:
                if r.status_code == 200:
                    return r.json()
                err = SourceError(f"HTTP {r.status_code} {url}: {r.text[:200]}")
                if r.status_code not in (429, 500, 502, 503, 504):
                    raise err
            if attempt < self.retries:
                time.sleep(65 if "429" in str(err) else 2 * 2**attempt)
        raise err


class VCI:
    """Vietcap: OHLCV ngày (cả mã đã huỷ niêm yết), danh sách mã, BCTC có ngày công bố."""

    name = "VCI"

    def __init__(self, min_interval: float = 1.0):
        self.http = HttpClient(
            min_interval=min_interval,
            headers={
                "Referer": "https://trading.vietcap.com.vn/",
                "Origin": "https://trading.vietcap.com.vn",
            },
        )

    # ---------- giá ----------
    def ohlcv(self, symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
        """Giá ngày [start, end]. Cột: date, open, high, low, close, volume (VND, cổ phiếu)."""
        end_ts = pd.Timestamp(end) if end else pd.Timestamp.today().normalize()
        start_ts = pd.Timestamp(start)
        # API trả `countBack` phiên kết thúc trước `to`; xin dư một chút rồi cắt theo start.
        count_back = len(pd.bdate_range(start_ts, end_ts)) + 10
        payload = {
            "timeFrame": "ONE_DAY",
            "symbols": [symbol],
            "to": int((end_ts + pd.Timedelta(days=1)).timestamp()),
            "countBack": count_back,
        }
        js = self.http.request("POST", f"{VCI_TRADING}/chart/OHLCChart/gap-chart", json=payload)
        if not js or not js[0].get("t"):
            raise SourceError(f"VCI không có giá cho {symbol}")
        df = parse_vci_ohlc(js[0], start_ts, end_ts)
        if df.empty:  # vd mã đã huỷ niêm yết trước `start`
            raise SourceError(
                f"{symbol}: không có phiên nào trong {start_ts.date()} → {end_ts.date()}"
            )
        return df

    # ---------- danh sách mã ----------
    def listing(self) -> pd.DataFrame:
        """Mọi mã VCI biết, gồm cả board == 'DELISTED' (hữu ích để chống survivorship bias)."""
        js = self.http.request("GET", f"{VCI_TRADING}/price/symbols/getAll")
        df = pd.DataFrame(js)
        keep = ["symbol", "type", "board", "organName", "enOrganName", "icbCode2"]
        return df[[c for c in keep if c in df.columns]]

    # ---------- báo cáo tài chính ----------
    def financials(self, symbol: str, section: str) -> pd.DataFrame:
        """Một loại BCTC, cả năm và quý, dạng rộng: mỗi dòng = 1 kỳ, cột mã chỉ tiêu (isa1...).

        `available_at` ưu tiên ngày công bố. Khi dùng số liệu VCI đã điều chỉnh,
        `available_at_conservative` tính cả ngày VCI cập nhật bản báo cáo.
        """
        js = self.http.request(
            "GET",
            f"{VCI_IQ}/company/{symbol}/financial-statement",
            params={"section": FIN_SECTIONS[section]},
        )
        return parse_vci_financials(js.get("data") or {}, symbol)

    def financial_fields(self, symbol: str = "FPT") -> pd.DataFrame:
        """Bảng tra mã chỉ tiêu → tên tiếng Việt/Anh (vd isa1 → 'Doanh thu bán hàng...')."""
        js = self.http.request("GET", f"{VCI_IQ}/company/{symbol}/financial-statement/metrics")
        rows = []
        for sec, items in (js.get("data") or {}).items():
            for it in items:
                rows.append(
                    {
                        "section": sec.lower(),
                        "field": it.get("field"),
                        "level": it.get("level"),
                        "parent": it.get("parent"),
                        "title_vi": it.get("titleVi"),
                        "title_en": it.get("titleEn"),
                    }
                )
        return pd.DataFrame(rows)


class KBS:
    """KB Securities: chỉ dùng để kiểm chéo giá (không có mã đã huỷ niêm yết)."""

    name = "KBS"

    def __init__(self, min_interval: float = 1.0):
        self.http = HttpClient(min_interval=min_interval)

    def ohlcv(self, symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
        end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
        fmt = "%d-%m-%Y"
        js = self.http.request(
            "GET",
            f"{KBS_IIS}/stocks/{symbol}/data_day",
            params={
                "sdate": pd.Timestamp(start).strftime(fmt),
                "edate": pd.Timestamp(end).strftime(fmt),
            },
        )
        rows = js.get("data_day") or []
        if not rows:
            raise SourceError(f"KBS không có giá cho {symbol}")
        df = pd.DataFrame(rows).rename(
            columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        )
        df["date"] = pd.to_datetime(df["t"]).dt.normalize()
        return df[["date", *OHLCV]].sort_values("date").reset_index(drop=True)


# ---------- parse thuần (test được offline) ----------
def parse_vci_ohlc(d: dict, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            # t là epoch giây tại 00:00 UTC (= 07:00 giờ VN) của ngày giao dịch
            "date": pd.to_datetime(pd.Series(d["t"]).astype("int64"), unit="s").dt.normalize(),
            "open": d["o"],
            "high": d["h"],
            "low": d["l"],
            "close": d["c"],
            "volume": d["v"],
        }
    )
    df = df[(df["date"] >= start) & (df["date"] <= end)]
    df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype("float64")
    df["volume"] = df["volume"].astype("Int64" if df["volume"].isna().any() else "int64")
    return df


def parse_vci_financials(data: dict, symbol: str) -> pd.DataFrame:
    frames = []
    for key, ptype in (("years", "year"), ("quarters", "quarter")):
        rows = data.get(key) or []
        if rows:
            f = pd.DataFrame(rows)
            f.insert(0, "period_type", ptype)
            frames.append(f)
    if not frames:
        raise SourceError(f"VCI không có BCTC cho {symbol}")
    df = pd.concat(frames, ignore_index=True)
    df = df.rename(
        columns={
            "yearReport": "fiscal_year",
            "lengthReport": "fiscal_quarter",  # 1-4 = quý, 5 = cả năm
            "publicDate": "public_date",
            "createDate": "created_at",
            "updateDate": "updated_at",
        }
    )
    for c in ("public_date", "created_at", "updated_at"):
        df[c] = pd.to_datetime(df.get(c, pd.NaT), format="mixed", errors="coerce")
    # Ưu tiên ngày công bố. Khi thiếu, ngày VCI nhập chỉ là ước tính và có thể sớm hơn.
    df["available_at"] = df["public_date"].fillna(df["created_at"]).dt.normalize()
    df["available_at_conservative"] = df[["public_date", "updated_at"]].max(axis=1).dt.normalize()
    df["ticker"] = symbol
    return df.drop(columns=["organCode"], errors="ignore")
