---
name: alpha-report-analyzer
description: Analyze MT5 Strategy Tester HTML reports with AlphaFactory and produce standardized JSON/CSV artifacts (enhanced_summary, weaknesses, by_session/hour/weekday, charts). Use when you have a report.html and need normalized metrics and breakdowns.
---

## Lệnh chuẩn
- `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" analyze -Report "<PATH_TO_REPORT.html>" -Charts`

## Output cần đọc (đọc trước theo thứ tự)
- `analysis\\enhanced_summary.json` (Trades/PF/DD/Net/WR/Expectancy)
- `analysis\\weaknesses.json` (issues theo severity)
- `analysis\\by_session.csv`, `analysis\\by_hour.csv`, `analysis\\by_weekday.csv`
- (nếu `-Charts`) `analysis\\analysis_charts.png`

## Quy tắc diễn giải (robustness-first)
- Không kết luận nếu trades quá ít.
- Nếu đổi 1 gate mà metrics không đổi → gate không binding hoặc nằm sau gate khác.

