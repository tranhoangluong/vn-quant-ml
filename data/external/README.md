# data/external

Dữ liệu tự thu thập thủ công, **được phép commit** (nhỏ, không có bản quyền):

- `vn30_membership.csv`: lịch sử thành phần VN30 theo từng kỳ review (tháng 1 và tháng 7),
  lấy từ thông cáo của HOSE. Cột: `effective_date,ticker,action` (`action` = add|remove),
  hoặc dạng snapshot `effective_date,ticker`. Đây là chỗ xử lý survivorship bias,
  rủi ro lớn nhất của dữ liệu miễn phí.
- `holidays_vn.csv`: ngày nghỉ lễ sàn HOSE (nếu cần lịch giao dịch chuẩn).
