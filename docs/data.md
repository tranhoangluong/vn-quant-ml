# Dữ liệu

| Nguồn | Nội dung | Cách lấy | Rủi ro |
|---|---|---|---|
| vnstock (VCI/TCBS) | OHLCV ngày đã điều chỉnh, 2014 → nay | `make data` | Giá điều chỉnh có thể thay đổi hồi tố; rate limit |
| HOSE (thông cáo) | Thành phần VN30 mỗi kỳ review | Nhập tay vào `data/external/vn30_membership.csv` | Thiếu kỳ → survivorship bias |
| CafeF | Kiểm chéo giá, sự kiện quyền | Tải tay khi cần | |
| Kenneth French library | (tuỳ chọn) dữ liệu Mỹ để kiểm định ngoài mẫu | | |

Ghi lại ngày tải dữ liệu (snapshot) trong luận văn vì nguồn miễn phí có thể sửa lịch sử.
