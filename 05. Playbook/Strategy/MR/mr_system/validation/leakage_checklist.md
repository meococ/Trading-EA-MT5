# Leakage Checklist — theo spec v3 §2.2 (tick từng mục trước khi tin backtest)

- [ ] Mọi feature tính trên bar ĐÃ ĐÓNG (loader dùng `copy_rates_from_pos(..., 1, n)` — bar 0 bị bỏ)
- [ ] Quyết định tại OPEN bar t; mọi rolling param kết thúc ở bar t−1
- [ ] H4 bias dùng bar H4 đã đóng gần nhất (không dùng bar H4 đang chạy)
- [ ] Backtest khớp giá open bar t + slippage model (không khớp close bar tín hiệu)
- [ ] SL và TP cùng chạm trong 1 bar → giả định SL trước (worst-case) khi chưa có tick data
- [ ] News filter dùng SCHEDULED time (không dùng thời điểm biết kết quả)
- [ ] mu_e, sig_e, HL_e, R ĐÓNG BĂNG tại entry (trailing dùng ATR rolling t−1 — duy nhất)
- [ ] Server time → UTC convert đúng DST (kiểm tra 2 tuần lệch US/EU tháng 3 & 10-11)
- [ ] Log 3 timestamp/lệnh: feature_time, decision_time, execution_time
- [ ] Indicator Python parity với MT5 (export CSV iATR/iADX từ MT5, so sánh, sai số < 1e-6)
- [ ] Trial registry ghi MỌI config đã chạy (input N của DSR — §10 Gate 3)
