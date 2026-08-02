# Quy Trình Thu Thập Dữ Liệu Zero-Trade (Data Acquisition Pipeline)

Quy trình độc lập cho các tác vụ thu thập dữ liệu / đồng bộ hóa tick & bar MT5 mà không đánh giá hiệu suất kinh tế.

## Điều Kiện Hợp Lệ Của Data-Acquisition

- Contract có authority `DATA_ACQUISITION_ONLY_NO_PERFORMANCE` hoặc `DATA_ACQUISITION_ONLY`.
- Package EA là no-trade canonical EA với `telemetry_profile=none` và `TelemetryTier=off`.
- Mọi công tắc giao dịch (`NoTrades`, `CollectionOnly`) đều là `true`.
- Báo cáo và summary xác thực **0 trades** (`performance_metrics_authorized=false`).

## Các Bước Thực Thi Data-Acquisition

1. **Preflight & Lock Storage**:
   - Xác nhận path lưu trữ dữ liệu nằm trên ổ D: (`02. AlphaFactory/data/`).
   - Snapshot 4 C-roots trước khi khởi chạy terminal MT5 (`02. AlphaFactory/tools/research/snapshot_c_roots.ps1`).

2. **Khởi Chạy Data Acquisition Run**:
   - Chạy lệnh thu thập qua `ea_research_loop.ps1`.
   - Sentinel request `requested_from=1970.01.01` đại diện cho yêu cầu lấy toàn bộ dữ liệu lịch sử khả dụng của broker.

3. **Validation & Evidence Ledger**:
   - Kiểm tra journal log để ghi nhận ngày khả dụng đầu tiên thực tế của broker per symbol (`history synchronized from...`).
   - Kiểm tra `04. Memory/research/validate_data_epoch.py` đối với contract data epoch tương ứng.
   - Nếu xuất hiện bất kỳ trade nào -> Reject run ngay lập tức như lỗi harness.

## Các Điều Cấm Trong Data Acquisition

- KHÔNG tính toán hay trích dẫn Profit Factor, Win Rate, Expectancy hay Cadence.
- KHÔNG gọi `validate-full` về mặt kinh tế hay tạo Heavy-Delivery casebook.
- KHÔNG tự động suy rộng việc broker thiếu dữ liệu trước 2018 thành "symbol không có edge".
