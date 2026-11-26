# Dữ liệu

| Nguồn | Nội dung | Cách lấy | Rủi ro |
|---|---|---|---|
| API web Vietcap (VCI) | OHLCV ngày đã điều chỉnh 2014 → nay (cả mã huỷ niêm yết), BCTC từ 2018 có ngày công bố, chỉ số VN30 | `make data` | API nội bộ, có thể đổi; giá điều chỉnh đổi hồi tố; thiếu mã sáp nhập |
| API web KBS | OHLCV từ ~2017 | `check_data.py --crosscheck` | Chỉ kiểm chéo, không có mã huỷ niêm |
| HOSE (thông cáo) | Thành phần VN30 mỗi kỳ review | Nhập tay vào `data/external/vn30_membership.csv` | Thiếu kỳ → survivorship bias |
| CafeF | Kiểm chéo giá, sự kiện quyền | Tải tay khi cần | |
| Kenneth French library | (tuỳ chọn) dữ liệu Mỹ để kiểm định ngoài mẫu | | |

Ghi lại ngày tải dữ liệu (snapshot) trong luận văn vì nguồn miễn phí có thể sửa lịch sử.

Hướng dẫn chi tiết từng bước: [data_guide.md](data_guide.md). Thư viện vnstock bị PyPI cách ly từ 09/2026 nên không còn dùng.
