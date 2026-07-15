---
name: alpha-execution-quality
description: Diagnose execution/microstructure issues from MT5 report + trade logs (session/hour weakness, fast SLs, stop distance, partial behavior). Use when PF drops in specific hours or DD spikes.
---

## Lệnh chạy
- Chuẩn hóa breakdown theo session/hour/weekday:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" analyze -Report "<PATH_TO_REPORT.html>" -Charts`

## Output cần đọc
- `analysis\\weaknesses.json` (đặc biệt type=hour/session)
- `analysis\\by_hour.csv`, `analysis\\by_session.csv`
- `analysis\\datalog\\trades_summary.json` (AchievedR + by_close_reason)

## Dấu hiệu execution/microstructure xấu (heuristics)
- PF rất thấp tập trung ở 1–3 giờ cụ thể (vd 15–16) → dễ liên quan spread/liquidity/news.
- Loss tail nặng: `AchievedR` p10 quá thấp và %SL cao → stop placement/volatility filter có vấn đề.
- CloseReason bất thường (nhiều `SL` liên tiếp, hoặc partial làm giảm payoff) → cần xem lại BE/trailing/partial.

## Quy tắc quyết định (gợi ý)
- Nếu weakness theo hour/session **lặp lại qua nhiều symbol/regime** → ưu tiên fix bằng filter “microstructure” (hours/session blacklist, spread cap, max trades/day).
- Nếu weakness chỉ xuất hiện 1 symbol hoặc 1 giai đoạn → coi là regime-specific, cần kiểm thêm WFA/Monte Carlo.

## Gợi ý hành động (thường hiệu quả)
- Thêm/tighten spread filter trước khi đặt lệnh.
- Tránh các giờ bị cảnh báo trong `weaknesses.json`.
- Giới hạn SL tối đa theo ATR, và tránh entry khi ATR spike.

