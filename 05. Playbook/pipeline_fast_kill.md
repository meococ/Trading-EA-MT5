# Quy Trình Fast-Kill Tinh Gọn (Fast-Kill Pipeline)

Quy trình lean dành riêng cho việc đóng các hypothesis / cell thử nghiệm bị vi phạm fatal gate sớm mà không phải chịu chi phí lễ nghi casebook hay AI review.

## Điều Kiện Áp Dụng Fast-Kill

- Hypothesis có `PREREG` hoặc `PROBE_PLAN` đã đóng băng pre-outcome.
- Chạm ngưỡng fatal gate đã khai báo trước (ví dụ: Profit Factor < 1.0 sau N completed trades, Max DD vượt budget, hoặc zero trade do trigger không thỏa).
- Model 0 run đã hoàn tất và có báo cáo/metrics cơ bản.

## Các Bước Thực Thi Fast-Kill

1. **Log Triage & Reconciliation**:
   - Trích xuất metrics cơ bản và kiểm tra log bằng `log_triage.py`.
   - Bắt buộc xác nhận không có lỗi kỹ thuật (engineering error) làm sai lệch kết quả backtest.

2. **Đóng Gói Fast-Kill Packet**:
   - Tạo file `FAST_KILL_CLOSEOUT.json` từ template `02. AlphaFactory/templates/research/FAST_KILL_CLOSEOUT.template.json`.
   - Bind thông tin hypothesis, source hash, compile log, report path và fatal gate bị trượt.

3. **Validate & Chuyển Trạng Thái Registry**:
   - Chạy lệnh:
     ```powershell
     powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory/alpha.ps1" fast-kill -Packet "<FAST_KILL_CLOSEOUT.json>"
     ```
   - Cập nhật trạng thái registry sang `KILLED` hoặc `PARKED`.

## Các Điều Cấm Trong Fast-Kill

- KHÔNG vẽ chart casebook anatomy.
- KHÔNG gọi Grok CLI hay sub-agent review hình ảnh.
- KHÔNG dùng Fast-Kill packet để tuyên bố hoàn thành mục tiêu chiến lược của workspace (Outcome book vẫn là `UNMET`).
- KHÔNG suy rộng lỗi data/engineering thành "thị trường không có edge".
