# Lộ trình (24 tuần, 23/11/2026 → 09/05/2027)

Chi tiết trong tài liệu kế hoạch của dự án. Mốc theo thư mục code:

| Tuần | Việc | Thư mục chính |
|---|---|---|
| 1–3 | Dữ liệu, universe VN30 point-in-time, EDA | `data/`, `notebooks/01` |
| 4–6 | Feature, nhãn, walk-forward, baseline momentum/Ridge | `features/`, `labels/`, `evaluation/splits.py` |
| 7–10 | LightGBM, tuning, chẩn đoán | `models/`, `notebooks/03` |
| 11–12 | Nghỉ Tết | |
| 13–16 | Conformal: split, ACI, DtACI, coverage | `uncertainty/`, `notebooks/04` |
| 15–18 | Danh mục + backtest có ràng buộc VN, ablation | `portfolio/`, `backtest/` |
| 18–20 | DSR, PBO, robustness; (tuỳ chọn) S&P 500, MLP | `evaluation/overfitting.py` |
| 19–24 | Viết luận văn, dashboard, slide bảo vệ | `thesis/`, `app/` |

Thứ tự cắt nếu trễ: S&P 500 → MLP → dashboard.
