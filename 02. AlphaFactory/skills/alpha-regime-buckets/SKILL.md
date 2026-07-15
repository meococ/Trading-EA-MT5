---
name: alpha-regime-buckets
description: Break down strategy performance by regime proxies (year/month/week buckets + trend regime) to detect regime-dependence and hidden overfitting. Use after baseline run has enough trades.
---

## Lệnh chạy
- Chuẩn hóa artifacts từ report (session/hour/weekday + weaknesses):
  - `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" analyze -Report "<PATH_TO_REPORT.html>" -Charts`
- Tạo breakdown theo năm/tháng/tuần (parser định lượng, phù hợp kiểm regime bằng proxy thời gian):
  - `python "02. AlphaFactory\\analysis\\quant_analyzer.py" --report "<PATH_TO_REPORT.html>" --out "<OUT_DIR>"`

## Output cần đọc
- Từ `alpha.ps1 analyze`:
  - `analysis\\enhanced_summary.json`
  - `analysis\\weaknesses.json`
  - `analysis\\by_session.csv`, `analysis\\by_hour.csv`, `analysis\\by_weekday.csv`
- Từ `quant_analyzer.py` (`<OUT_DIR>`):
  - `yearly.csv`, `monthly.csv`, `weekly.csv`
  - `summary.json`

## Quy tắc quyết định (gợi ý, robustness-first)
- Nếu có **>= 1 năm** PF < 0.9 hoặc Net âm lớn → coi là **regime risk** (dễ sập khi đổi chế độ thị trường).
- Ưu tiên chiến lược có hiệu suất **không “gãy”**: đa số năm PF >= 1.1, và không có năm drawdown/Net quá cực đoan.
- Nếu sample theo năm quá ít trades → chỉ coi là tín hiệu tham khảo, cần tăng sample (multi-symbol).

## Gợi ý hành động khi phát hiện năm/tháng xấu
- Năm shock/volatility (vd 2020): xem lại spread filter, volatility filter, max SL, session/hours blacklist.
- Tháng xấu lặp lại theo mùa (Aug/Dec…): kiểm tra thanh khoản/thời điểm tin tức.

