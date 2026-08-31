---
name: alpha-datalog-db
description: Treat EA signal/trade CSV logs as a backtest database. Use when you want gate-binding analysis (SkipReason/gate_fail), achievedR distribution, and trade attribution from AlphaFactory datalog outputs.
---

## Nguồn dữ liệu (AlphaFactory tự copy khi backtest)
- Logs (raw): `02. AlphaFactory\\runs\\<EA>\\<RUN_ID>\\analysis\\logs\\`
  - `<SYMBOL>_Signals_*.csv`
  - `<SYMBOL>_Trades_*.csv`

## Analyzer (AlphaFactory gọi tự động sau backtest nếu có)
- `02. AlphaFactory\\analysis\\datalog_analyzer.py`

## Output chuẩn để đọc như “database”
- `02. AlphaFactory\\runs\\<EA>\\<RUN_ID>\\analysis\\datalog\\signals_summary.json`
  - `executed/skipped`
  - `skip_reason` (đếm theo lý do)
  - `gate_fail` (gate nào fail nhiều nhất)
- `...\\analysis\\datalog\\trades_summary.json`
  - `AchievedR` p10/p50/p90, mean
  - `%>=2R`, `%>=3R`
  - `by_close_reason`

## Cách dùng (ngắn gọn)
- Chọn 1 giả thuyết (vd: tắt 1 gate).
- So sánh 2 run:
  - Trades thay đổi?
  - `skip_reason`/`gate_fail` thay đổi?
  - `AchievedR` tail (p90) thay đổi?

