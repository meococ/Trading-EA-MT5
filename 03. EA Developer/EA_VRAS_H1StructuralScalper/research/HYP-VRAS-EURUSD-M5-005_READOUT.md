# HYP-VRAS-EURUSD-M5-005 — Terminal Readout (Corrected MT5 Report Gốc)

> **VERDICT: TERMINAL KILL / PROMOTION-INELIGIBLE**  
> `KILL_CURRENT_HYP005_INVALID_AND_LOSS_MAKING`

## Summary Audit

Thẩm định forensic trực tiếp từ **MT5 Report Gốc (`report.html`)** bác bỏ hoàn toàn báo cáo sơ bộ bị lệch từ file lifecycle CSV thiếu hụt. 

- Báo cáo sơ bộ trước đó bị lỗi do `WriteLifecycleTrade()` trong code MQL5 chỉ được gọi tại `CheckTimeExits()`, thiếu hàm `OnTradeTransaction()` để ghi nhận các lệnh chạm SL/TP do broker kích hoạt. 
- Hậu quả: File CSV thiếu mất 207 lệnh SL/TP (đặc biệt là 178 lệnh lỗ), chỉ ghi lại 115 lệnh time-exit (+ $3,964.92), tạo ra chênh lệch đối soát (reconciliation gap) lên tới **-$14,005.78**.

## Bảng Đối Soát Số Liệu Thực Tế (MT5 Report Gốc vs Báo Cáo Sơ Bộ)

| Chỉ số Metric | Báo Cáo Sơ Bộ (Chỉ 115 Time-Exits) | MT5 Report Gốc (Toàn Bộ 322 Trades) | Trạng Thái / Verdict |
|---|---:|---:|---|
| **Net Profit** | +$3,964.92 | **-$10,040.86** | **THUA LỖ NẶNG (-$10k)** |
| **Profit Factor (PF)** | 1.9205 | **0.74** | **TRƯỢT (Target ≥ 1.30)** |
| **Win Rate** | 54.78% (63/50) | **44.72%** (144 thắng / 178 thua) | **TRƯỢT** |
| **Số Lượng Lệnh** | "115 closed" | **322 trades / 644 deals** | Lệnh bị cháy/stop-out ngày 21/03/2019 |
| **Tần Suất (Cadence)** | 1.55 lệnh/tuần (chia 4 năm) | **28.69 lệnh/tuần** (trong 11.22 tuần) | **VI PHẠM (Quá nhiều whipsaw)** |
| **Equity Drawdown** | 6.00% | **12.71%** | **VI PHẠM TRẦN 6.0%** |
| **Balance Drawdown** | 0.46% | **12.45%** | **VI PHẠM TRẦN 6.0%** |
| **Expectancy / Trade** | +$34.48 | **-$31.18 / lệnh** | **KỲ VỌNG ÂM** |
| **Final Balance** | ~$103,964.92 | **$89,959.14** | **Bị Stop-out tài khoản** |

## Chi Tiết Các Lỗi Kỹ Thuật & Cấu Trúc Code:

1. **Lỗi Ghi Log Telemetry**: Thiếu `OnTradeTransaction()`, dẫn đến mất 207 dòng log CLOSE chạm SL/TP, làm sai lệch báo cáo reconciliation.
2. **Sai Spec Chỉ Báo (Rolling VWAP)**: Code dùng `CalculateSessionVWAP(48)` (trung bình trượt 48 nến M5), vi phạm Prereg quy định Session VWAP / Anchored AVWAP theo khung giờ London.
3. **Các Tầng Guard Thiếu Call-path**: `InpMaxAccountDrawdownPct`, `InpDailyLossPct`, `InpMaxTradesPerDay` và News Guard được khai báo input nhưng không được gọi trong `OnTick()`.
4. **Cadence Sai Lệch**: Backtest bị dừng ngày 21/03/2019 do Stop-out (chỉ mới chạy 5% window 2019-2022). Cadence thực tế là 28.69 lệnh/tuần (whipsaw nặng), không phải 1.55 lệnh/tuần.
5. **Registry Hash Drift**: Registry row ghi SHA256 `09D4...` lệch với SHA256 code đã chạy `93DC...`.

## Quyết Định Cuối Cùng

- **KILLED**: `HYP-VRAS-EURUSD-M5-005` bị dừng vĩnh viễn với phán quyết **`KILL_CURRENT_HYP005_INVALID_AND_LOSS_MAKING`**.
- Không thực hiện bất kỳ hành động Post-hoc rescue, retune, hay chạy Monte Carlo / Cost Stress trên kết quả vô hiệu này.
