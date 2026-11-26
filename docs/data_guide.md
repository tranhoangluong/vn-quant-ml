# Hướng dẫn lấy dữ liệu và lưu ra parquet

> Viết ngày 26/11/2026. Mọi lệnh và con số dưới đây đều đã chạy thật trên dữ liệu thật vào
> ngày này (Python 3.13, pandas 3.1, pyarrow 26), với 6 mã thử: FPT, VNM, MWG (đang niêm yết),
> ROS, FLC (đã huỷ niêm yết), BHS (đã sáp nhập).

## 0. Tóm tắt trong 5 dòng

1. **Không dùng thư viện vnstock nữa.** PyPI đã cách ly (quarantine) gói `vnstock` và `vnai`
   từ khoảng 24/09/2026, nên `pip install vnstock` báo "No matching distribution". Theo README
   chính thức, mọi bản trước "thế hệ 6" ngừng hoạt động từ 10/11/2026; thế hệ 6 cài từ kho riêng
   của vnstocks.com và yêu cầu bạn tự có tài khoản/khoá do nguồn dữ liệu cấp.
2. Thay vào đó repo gọi **thẳng API công khai của Vietcap (VCI)**, đúng các endpoint mà vnstock
   3.x từng gọi, chỉ cần `requests`. KBS dùng để kiểm chéo giá.
3. `python scripts/01_download_data.py` → `data/raw/snapshot=<ngày tải>/` gồm giá, chỉ số, BCTC,
   danh sách mã, và `_manifest.json` ghi ngày tải, nguồn, phiên bản thư viện, commit git.
4. `python scripts/check_data.py` kiểm tra chất lượng, kiểm chéo VCI với KBS.
5. VCI **có giá của mã đã huỷ niêm yết** (ROS, FLC). Mã đã sáp nhập (BHS) thì **không có**.
   BCTC của VCI chỉ có **từ 2018**, nhưng có **ngày công bố**, rất quý để chống look-ahead.

## 1. Cài đặt

```bash
cd vn-quant-ml
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[data,dev]"                            # data = requests (không còn vnstock)
pytest -q                                               # 14 test offline phải pass
pytest -q -m integration                                # 1 test gọi API thật (cần mạng)
```

## 2. Hiểu nguồn trước đã: gọi API bằng tay

Chạy đoạn này trong Jupyter để thấy dữ liệu thô trông thế nào. Đây là toàn bộ "phép màu" mà
vnstock làm cho phần giá.

```python
import requests, pandas as pd

H = {"User-Agent": "Mozilla/5.0 (academic research)",
     "Referer": "https://trading.vietcap.com.vn/", "Origin": "https://trading.vietcap.com.vn"}
r = requests.post(
    "https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart",
    json={"timeFrame": "ONE_DAY", "symbols": ["FPT"],
          "to": int(pd.Timestamp("2026-11-27").timestamp()),   # lấy các phiên TRƯỚC mốc này
          "countBack": 5},                                     # số phiên muốn lấy
    headers=H, timeout=30)
print(r.json())
```

Kết quả (rút gọn):

```
[{"symbol":"FPT","o":[46950,45600,...],"h":[...],"l":[...],"c":[45700,45000,...],
  "v":[18437700,...],"t":["1795046400","1795132800",...]}]
```

- `o h l c v` là các mảng song song; `t` là epoch giây lúc 00:00 UTC (= 7:00 sáng giờ VN) của
  ngày giao dịch.
- Giá tính bằng **đồng** (45700 = 45.700 đ), **đã điều chỉnh** theo cổ tức/chia tách (giá năm 2014
  có số lẻ như 5100.93 là dấu hiệu đã điều chỉnh).
- Một lần gọi lấy được hết lịch sử từ 2014 (khoảng 3.200 phiên), không cần chia nhỏ.

Các endpoint khác repo dùng:

| Mục đích | Endpoint |
|---|---|
| Danh sách mọi mã (có `board = DELISTED`) | `GET https://trading.vietcap.com.vn/api/price/symbols/getAll` |
| BCTC | `GET https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/{mã}/financial-statement?section=INCOME_STATEMENT` (hoặc `BALANCE_SHEET`, `CASH_FLOW`) |
| Tên chỉ tiêu BCTC | `GET .../company/{mã}/financial-statement/metrics` |
| Kiểm chéo giá (KBS) | `GET https://kbbuddywts.kbsec.com.vn/iis-server/investment/stocks/{mã}/data_day?sdate=01-01-2019&edate=31-12-2019` |

**Lưu ý quan trọng:** đây là API nội bộ của website, không phải API công bố chính thức. Chúng có
thể đổi hoặc chặn bất cứ lúc nào. Vì vậy: gọi chậm (repo mặc định 1 request/giây), không tải lặp
vô ích, và **giữ snapshot đã tải** để luận văn không phụ thuộc vào việc API còn sống.

## 3. Tải dữ liệu bằng repo

Code nằm ở:

- `src/vnqml/data/sources.py`: lớp `VCI` (giá, danh sách mã, BCTC) và `KBS` (kiểm chéo), có
  giãn cách và thử lại khi lỗi 429/5xx.
- `src/vnqml/data/store.py`: ghi/đọc parquet, manifest, kiểm tra, so sánh snapshot.
- `scripts/01_download_data.py`: chạy toàn bộ bước tải.

Thử nhanh với vài mã (chưa cần điền danh sách VN30):

```bash
python scripts/01_download_data.py --tickers FPT,VNM,MWG,ROS,FLC,BHS
```

Log thật (rút gọn), khoảng 30 giây:

```
Snapshot 2026-11-26: 6 mã, 2014-01-01 → None, nguồn VCI
WARNING Không có trong danh sách VCI (có thể đã sáp nhập/đổi mã): ['BHS']
WARNING prices BHS: VCI không có giá cho BHS
prices                       FLC    2626 dòng
prices                       FPT    3217 dòng
prices                       ROS    1484 dòng
index                        VN30   3217 dòng
financials/income_statement  FPT      43 dòng
...
Xong snapshot 2026-11-26. Ghi mới: {'prices': 5, 'index': 2, ...}. Lỗi: {'prices': 1, ...}
```

Khi đã điền `data/external/vn30_membership.csv`, chạy không cần `--tickers`: script tự lấy mọi mã
**từng** có mặt trong rổ.

```bash
make data          # = 01_download_data.py + 02_build_dataset.py
make check-data    # = check_data.py --crosscheck FPT
```

Các tuỳ chọn:

| Lệnh | Tác dụng |
|---|---|
| `--no-financials` | chỉ lấy giá |
| `--snapshot 2026-11-26` | chạy tiếp một snapshot bị ngắt (file đã có sẽ bỏ qua) |
| `--force` | tải lại cả file đã có |

Thông số trong `configs/base.yaml`, mục `data:`: `start`, `end`, `index_symbols`,
`min_interval_sec`, và `snapshot` (bước 02 dùng snapshot nào; `null` = mới nhất).

## 4. Cấu trúc thư mục và lý do

```
data/raw/
├── LATEST                                   # chứa "2026-11-26"
└── snapshot=2026-11-26/
    ├── _manifest.json                       # ngày tải, nguồn, endpoint, phiên bản, lỗi
    ├── listing.parquet                      # 3.894 mã, trong đó 1.738 DELISTED
    ├── prices/
    │   ├── ticker=FPT/part-0.parquet        # date, open, high, low, close, volume
    │   └── ticker=ROS/part-0.parquet
    ├── index/ticker=VN30/part-0.parquet     # VN30, VNINDEX
    └── financials/
        ├── fields.parquet                   # isa1 → "Doanh thu bán hàng và cung cấp dịch vụ"
        ├── section=balance_sheet/ticker=FPT/part-0.parquet
        ├── section=income_statement/ticker=FPT/part-0.parquet
        └── section=cash_flow/ticker=FPT/part-0.parquet
```

Ba quyết định thiết kế:

1. **Mỗi lần tải là một snapshot riêng, không nối thêm vào file cũ.** Giá đã điều chỉnh bị nguồn
   tính lại *toàn bộ quá khứ* mỗi khi có chia cổ tức bằng cổ phiếu; BCTC bị ghi đè khi doanh
   nghiệp điều chỉnh (cột `updated_at` cho thấy). Nối thêm sẽ trộn hai thang giá khác nhau.
   Tải lại toàn bộ VN30 chỉ mất vài phút nên không cần "incremental".
2. **Chia thư mục theo mã (`ticker=FPT`)** theo kiểu Hive: tải lỗi một mã thì chạy lại đúng mã đó;
   đọc vài mã không phải mở cả bộ; pandas/pyarrow/DuckDB/Polars đều tự hiểu `ticker=` là một cột.
3. **Metadata đi theo dữ liệu**, ở hai chỗ: `_manifest.json` cho cả snapshot, và JSON nhúng trong
   schema của từng file parquet (nguồn, ngày giờ tải, số dòng). File ghi ra file tạm rồi mới đổi tên,
   nên bị ngắt giữa chừng cũng không để lại file hỏng.

`data/raw/` không commit (đã có trong `.gitignore`). Riêng `data/external/` **được** commit:
repo gốc lỡ ignore cả thư mục này, bản cập nhật đã sửa để `vn30_membership.csv` lên được GitHub.

## 5. Đọc lại dữ liệu

```python
import pandas as pd
from vnqml.data import store

prices = store.read_prices("data/raw")                        # snapshot mới nhất, mọi mã
prices = store.read_prices("data/raw", "2026-11-26", tickers=["FPT", "ROS"])
prices.tail(3)
#             date ticker     open     high      low    close   volume
# 13632 2026-11-23    VNM  51400.0  52500.0  51100.0  52300.0  2132095
# 13633 2026-11-25    VNM  52300.0  53100.0  52300.0  52500.0  2795400
# 13634 2026-11-26    VNM  52400.0  53300.0  52400.0  52700.0  3247200

# Không cần vnqml cũng đọc được (cột ticker thành kiểu category):
df = pd.read_parquet("data/raw/snapshot=2026-11-26/prices")

# Metadata
store.read_meta("data/raw/snapshot=2026-11-26/prices/ticker=FPT/part-0.parquet")
# {'snapshot': '2026-11-26', 'source': 'VCI', 'client': 'vnqml-sources/0.1', 'ticker': 'FPT',
#  'fetched_at': '2026-11-26T13:03:01+00:00', 'rows': 3217}
store.read_manifest("data/raw")["environment"]
# {'python': '3.13.18', 'pandas': '3.1.1', 'pyarrow': '26.0.1', ..., 'git_commit': 'c5bc1bb'}
```

`scripts/02_build_dataset.py` đã được sửa để đọc bằng `store.read_prices(...)`, nên các bước sau
của pipeline không đổi.

## 6. Kiểm tra dữ liệu

```bash
python scripts/check_data.py --crosscheck FPT,VNM,ROS
```

Kết quả thật:

```
ticker  rows      first       last  dup  bad_ohlc  zero_vol  big_moves  max_gap    ok    board
   FLC  2626 2014-01-02 2024-07-25    0         0       462          0       14  True DELISTED
   FPT  3217 2014-01-02 2026-11-26    0         0         2          0       11  True      HSX
   MWG  3091 2014-07-14 2026-11-26    0         0         2          0       11  True      HSX
   ROS  1484 2016-09-01 2022-08-11    0         0         2          1       10  True DELISTED
   VNM  3217 2014-01-02 2026-11-26    0         0         2          0       11  True      HSX
[financials/income_statement] 172 kỳ, 5 mã, năm sớm nhất 2018, thiếu ngày công bố 0,
                              trễ công bố BCTC quý: trung vị 31 ngày, lớn nhất 367 ngày
[crosscheck VCI vs KBS] FPT: common_days 2542, median_price_ratio 0.9994, ret_corr 0.99999, ret_mismatch_days 0
[crosscheck VCI vs KBS] VNM: common_days 2505, median_price_ratio 0.9961, ret_corr 0.99995, ret_mismatch_days 0
[crosscheck VCI vs KBS] ROS: common_days 34, ret_mismatch_days 0
```

Cách đọc:

- `dup`, `bad_ohlc` phải bằng 0.
- `max_gap` 10–12 ngày là nghỉ Tết, bình thường. Lớn hơn 15 ngày thì bảng báo `ok = False`, nên
  xem lại (thường là mã bị đình chỉ giao dịch).
- `zero_vol` lớn (FLC 462 phiên) là giai đoạn bị đình chỉ hoặc hạn chế giao dịch. Bước 02
  (`basic_clean`) cần xử lý các phiên này, và đây cũng là điểm cần nói trong phần dữ liệu của luận văn.
- `big_moves` là số phiên lợi suất vượt ±7,5%. Trên HOSE thì đáng ngờ; nhưng mã có thể từng ở
  HNX (±10%) hoặc UPCoM (±15%), hoặc là ngày đầu niêm yết.
- Kiểm chéo: VCI và KBS lệch nhau một hệ số giá rất nhỏ (cách điều chỉnh khác nhau) nhưng
  **lợi suất ngày khớp hoàn toàn** (0 ngày lệch quá 0,5 điểm %). KBS chỉ có lịch sử từ khoảng
  2017 và gần như không có mã đã huỷ niêm yết, nên chỉ dùng để kiểm chéo, không dùng làm nguồn chính.

So sánh hai lần tải để đo mức "sửa lịch sử" (nên chạy mỗi tháng một lần và ghi vào luận văn):

```bash
python scripts/check_data.py --diff 2026-11-26      # so snapshot mới nhất với 2026-11-26
```

## 7. BCTC: dạng dữ liệu và join as-of

File BCTC ở dạng rộng: mỗi dòng là một kỳ (`period_type` = `year`/`quarter`, `fiscal_year`,
`fiscal_quarter` từ 1 đến 4, và 5 nghĩa là cả năm), mỗi cột là một mã chỉ tiêu (`isa1`, `bsa1`...).
Ngân hàng dùng bộ mã khác (`isb...`, `bsb...`), `fields.parquet` có đủ tên.

Các cột thời gian:

| Cột | Ý nghĩa |
|---|---|
| `public_date` | ngày doanh nghiệp công bố báo cáo (theo VCI) |
| `created_at` / `updated_at` | lúc VCI nhập và lần sửa gần nhất |
| `available_at` | ngày công bố, nếu thiếu thì lấy ngày VCI nhập (`created_at`), có thể sớm hơn ngày công bố thực tế |
| `available_at_conservative` | ngày muộn nhất trong `public_date` và `updated_at`, dùng khi xét bản báo cáo đã chỉnh sửa. Nếu chỉ có một mốc thì lấy mốc đó, nếu thiếu cả hai thì để trống |

```python
inc = store.read_dataset("data/raw", "financials", section="income_statement", tickers=["FPT", "VNM"])
fields = pd.read_parquet("data/raw/snapshot=2026-11-26/financials/fields.parquet")
long = store.tidy_financials(inc, fields)          # 1 dòng = (mã, kỳ, chỉ tiêu, giá trị, tên)

# LNST cổ đông công ty mẹ (isa22) theo quý, chỉ dùng từ phiên SAU ngày công bố
npq = (long.query("period_type == 'quarter' and field == 'isa22'")
           .assign(usable_from=lambda d: d["available_at"] + pd.Timedelta(days=1))
           [["ticker", "usable_from", "fiscal_year", "fiscal_quarter", "value"]]
           .rename(columns={"value": "np_parent"}).sort_values("usable_from"))
panel = pd.merge_asof(prices.sort_values("date"), npq, left_on="date", right_on="usable_from",
                      by="ticker", direction="backward")
```

Kiểm tra thật trên FPT: BCTC quý 3/2026 công bố ngày 29/10/2026; trong `panel`, ngày 29/10 vẫn dùng
số quý 2, từ 30/10 mới dùng số quý 3. Đây chính là cơ chế chống look-ahead mà file 05 yêu cầu.

Cộng thêm 1 ngày vì `public_date` không có giờ: báo cáo có thể ra sau giờ đóng cửa. Hạn chế cần
ghi trong luận văn: VCI ghi đè số liệu khi doanh nghiệp điều chỉnh, nên đây là số liệu *mới nhất*
của kỳ đó, chưa chắc là con số thị trường thấy vào ngày công bố.

## 8. Mã đã huỷ niêm yết: kết quả thử

| Mã | Tình trạng | Giá trên VCI | BCTC trên VCI |
|---|---|---|---|
| ROS (FLC Faros) | DELISTED | 01/09/2016 → 11/08/2022, 1.484 phiên | 2018–2021 |
| FLC (Tập đoàn FLC) | DELISTED | 2011 → 25/07/2024 (cả giai đoạn UPCoM) | có |
| BHS (Đường Biên Hoà, đã sáp nhập vào SBT) | không có trong danh sách | **không có** | không có |

Kết luận cho luận văn:

- Survivorship bias do **huỷ niêm yết** xử lý được bằng VCI: chỉ cần biết mã, lịch sử giá vẫn còn.
- Mã **sáp nhập/đổi mã** thì mất dữ liệu (ít nhất là BHS; cần thử từng trường hợp). Với VN30 từ 2014, cần lập danh sách
  các mã như vậy khi nhập `vn30_membership.csv`, rồi bổ sung giá từ CafeF/Vietstock (tải tay CSV, đọc
  bằng `loaders.load_csv_dir`), hoặc giới hạn mẫu và ghi rõ hạn chế.
- `listing.parquet` có 1.738 mã DELISTED, dùng để biết nhanh một mã còn giao dịch hay không.

## 9. Ghi gì vào luận văn (chương Dữ liệu, phụ lục tái lập)

- Nguồn: API web công khai của Vietcap Securities, truy cập ngày ... (tên snapshot).
- Giá ngày đã điều chỉnh, đơn vị VND, giai đoạn ..., N mã; kiểm chéo lợi suất với KBS.
- Phiên bản: lấy từ `_manifest.json` (Python, pandas, pyarrow, commit git của repo).
- Số mã thiếu dữ liệu (`failures` trong manifest) và cách xử lý.
- Kết quả `--diff` giữa hai snapshot, nếu có, làm bằng chứng về rủi ro sửa lịch sử.

## 10. Tải snapshot nghiên cứu cố định (2014 → nay) và đóng băng

Ý tưởng: tải **một lần**, đủ rộng để không phải tải lại, kiểm tra, rồi **đóng băng**. Toàn bộ
luận văn dùng đúng snapshot đó. Snapshot mới (nếu có) chỉ để đo mức nguồn sửa lịch sử.

**Vì sao tải mọi cổ phiếu chứ không chỉ VN30?** File `vn30_membership.csv` còn trống, và mã từng ở
VN30 có thể nay đã chuyển sang UPCoM/HNX hoặc huỷ niêm yết. `--universe all-stocks` lấy mọi cổ phiếu
VCI biết (HOSE 412, HNX 299, UPCoM 808, đã huỷ niêm yết 239 mã, tính ngày 26/11/2026), nên chắc chắn
chứa mọi mã VN30 mà VCI còn giữ dữ liệu. Sau này `in_universe` ở bước 02 sẽ lọc đúng rổ theo từng ngày.

**Bước 1. Chọn ngày chốt** (`--end`), ví dụ phiên gần nhất. Tên snapshot nên trùng ngày chốt.

**Bước 2. Tải** (khoảng 30 phút cho giá, thêm khoảng 1,5 giờ cho BCTC, ở tốc độ 1 request/giây):

```bash
python scripts/01_download_data.py --universe all-stocks \
    --start 2014-01-01 --end 2026-11-26 --snapshot 2026-11-26
# hoặc: make snapshot END=2026-11-26
```

Bị ngắt (mất mạng, tắt máy) thì chạy lại **đúng lệnh đó**: file đã có được bỏ qua, mã lỗi được thử
lại. Muốn chia làm hai lần: thêm `--no-financials` lần đầu, rồi chạy lại không có cờ này để bổ sung
BCTC vào cùng snapshot. Có thể giới hạn BCTC cho một danh sách mã bằng `--tickers-file vn30_all.txt`.

**Bước 3. Kiểm tra:**

```bash
python scripts/check_data.py --snapshot 2026-11-26 --crosscheck FPT,VNM,HPG
```

Với ~1.700 mã sẽ có nhiều mã nhỏ bị đánh dấu "CẦN XEM" (đình chỉ, ít giao dịch), bình thường. Điều
cần chú ý: `failures` trong manifest, và (khi đã điền file VN30) dòng **"Mã VN30 thiếu giá"**.

**Bước 4. Đóng băng và sao lưu:**

```bash
python scripts/freeze_snapshot.py --snapshot 2026-11-26 --zip --note "snapshot nghiên cứu chính"
python scripts/freeze_snapshot.py --snapshot 2026-11-26 --verify      # bất cứ lúc nào: "Nguyên vẹn."
```

Lệnh này ghi `_checksums.sha256` (SHA-256 từng file) và `_FROZEN`; từ đó `01_download_data.py` từ chối
ghi vào snapshot này. File zip cất lên Google Drive hoặc ổ ngoài, **không** commit lên GitHub. Trong
luận văn, ghi tên snapshot và mã SHA-256 của file zip.

**Bước 5. Ghim snapshot** trong `configs/base.yaml`: `data.snapshot: "2026-11-26"`, để `make data`,
`make features`... luôn đọc đúng bản này dù sau đó bạn tải thêm snapshot khác.

Kết quả thử thật với 239 mã đã huỷ niêm yết (4 phút): 205 mã có giá, 34 mã VCI không có giá. Mọi mã có
giá đều ngừng giao dịch từ 2022 trở đi; **mã huỷ niêm yết trước khoảng 2022 gần như không có trong
VCI** (ví dụ BHS). Đây là lỗ hổng survivorship chính còn lại: khi điền file VN30, `check_data.py` sẽ liệt
kê các mã thiếu để bạn lấy bù từ CafeF hoặc nêu rõ là hạn chế.

## 11. Việc tiếp theo

1. Nhập `data/external/vn30_membership.csv` từ thông cáo HOSE (việc thủ công lớn nhất). Ghi chú
   những mã sáp nhập/đổi mã.
2. Chạy `make data` với toàn bộ danh sách, rồi `make check-data`.
3. Xử lý phiên khối lượng 0 trong `basic_clean` (bỏ khỏi tập có thể giao dịch, không xoá khỏi panel).
4. Chạy lại `01_download_data.py` mỗi tháng để có snapshot mới, và chạy `--diff`.
