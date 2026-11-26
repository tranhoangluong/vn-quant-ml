# Kiến trúc dự án vn-quant-ml

## Luồng dữ liệu

```
API Vietcap (VCI)         data/external/vn30_membership.csv (thủ công, từ HOSE)
        │                              │
        ▼                              │
01_download_data ──► data/raw/snapshot=<ngày>/{prices,index,financials}/ticker=<mã>/
        │                              │
        ▼                              ▼
02_build_dataset ──► data/interim/panel.parquet
   (làm sạch, ret, cờ trần/sàn, in_universe point-in-time)
        │
        ▼
03_build_features ─► data/processed/dataset.parquet   (X đã rank tiết diện + y)
        │
        ▼
04_train_walkforward ─► experiments/<run>/predictions.parquet  (pred, lo, hi, y, fold)
   (LightGBM/Ridge/Momentum + Split/ACI/DtACI)          metrics_forecast.json
        │
        ▼
05_backtest ─────────► experiments/<run>/backtest.parquet      (gross, cost, net, turnover)
   (long-only, biên độ ±7%, T+2, phí + thuế)             metrics_portfolio.json
        │
        ▼
06_make_report ──────► reports/tables/summary.csv, thesis/tables/summary.tex (DSR, PBO)
```

Mỗi bước đọc đầu ra của bước trước từ đĩa, nên có thể chạy lại riêng từng bước.
Định dạng chuẩn ở mọi nơi: DataFrame **long format**, index `(date, ticker)`.

## Package `src/vnqml/`

| Module | Vai trò | Chương luận văn |
|---|---|---|
| `config.py` | Đọc YAML, `inherit:` để thí nghiệm chỉ ghi phần khác base | 4 (thiết lập) |
| `data/sources.py` | Gọi API VCI (giá, BCTC, danh sách mã) và KBS (kiểm chéo) | 3.1 Dữ liệu |
| `data/store.py` | Snapshot parquet chia theo mã, manifest, kiểm tra, diff snapshot | 3.1 |
| `data/loaders.py` | Đưa về panel (date, ticker), hoặc đọc CSV | 3.1 |
| `data/universe.py` | Rổ VN30 theo thời điểm, chống survivorship bias | 3.1 |
| `data/cleaning.py` | Làm sạch, lợi suất, cờ trần/sàn, winsorize tiết diện | 3.1 |
| `features/price.py` | Momentum, reversal, volatility, thanh khoản (Amihud), kỹ thuật | 3.2 Feature |
| `features/cross_section.py` | Rank / z-score theo ngày | 3.2 |
| `features/build.py` | Ghép nhóm feature theo config | 3.2 |
| `labels/forward_returns.py` | Lợi suất tương lai h phiên, excess / rank | 3.2 |
| `models/` | `BaseModel`, `LGBMModel`, baseline `MomentumRule`, `RidgeModel`, registry | 3.3 Mô hình |
| `uncertainty/conformal.py` | Split conformal, ACI, DtACI, có trễ phản hồi = horizon | 3.4 Bất định (đóng góp chính) |
| `portfolio/construction.py` | Top-k long-only, sizing theo khoảng conformal, giới hạn tỷ trọng | 3.5 Danh mục |
| `portfolio/constraints.py` | Chặn mua mã trần, bán mã sàn, khoá T+2, không short | 3.5 (đóng góp chính) |
| `portfolio/costs.py` | Phí môi giới + thuế bán | 3.5 |
| `backtest/engine.py` | Backtest ngày, tín hiệu close t → khớp close t+1 | 4 Thực nghiệm |
| `evaluation/splits.py` | Walk-forward expanding/rolling có embargo | 3.6 Đánh giá |
| `evaluation/walkforward.py` | Vòng lặp train → calibrate → test theo fold | 4 |
| `evaluation/metrics.py` | IC, ICIR, Sharpe, MaxDD, coverage | 4 |
| `evaluation/overfitting.py` | Deflated Sharpe Ratio, PBO (CSCV) | 3.6, 4 |
| `utils/` | I/O parquet, thư mục run có bản sao config, seed, logging | |

## Nguyên tắc

1. **Không look-ahead**: feature tại t chỉ dùng dữ liệu ≤ t; nhãn bắt đầu từ t+1; có test
   `tests/unit/test_no_lookahead.py` bảo vệ. Đây là lỗi phổ biến nhất khiến hội đồng bác kết quả.
2. **Notebook không chứa logic**: notebook chỉ gọi `vnqml` và vẽ hình.
3. **Mỗi kết quả trong luận văn truy được về một run**: `experiments/<run>/config.yaml`.
4. **Đếm mọi thí nghiệm đã thử** (kể cả thất bại) trong `docs/experiment_log.md` để tính DSR trung thực.
5. **Dữ liệu không commit** (trừ `data/external/`); ai cũng tái tạo được bằng `make data`.
