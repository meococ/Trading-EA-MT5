---
name: alpha-strategy-memory
description: Maintain strategy experiment memory using AlphaFactory STRATEGY_LOG.md and alpha.ps1 log command. Use after each backtest/robustness run to record results and lessons to avoid repeating failed ideas.
---

## Luật vàng
- Luôn đọc `02. AlphaFactory\\STRATEGY_LOG.md` trước khi đề xuất chiến lược/gate mới.
- Sau mỗi run quan trọng, phải ghi lại (PF/DD/Trades + lesson).

## Lệnh hỗ trợ
- Auto log từ report (AlphaFactory dùng đối số positional `$Name`):
  - `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" log "<LABEL>" -Report "<PATH_TO_REPORT_OR_RESULTS>"`
- Manual entry:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" log "<LABEL>"`

## Format khuyến nghị khi ghi
- RUN_ID / EA / Symbol / TF / From-To / Model / Overrides
- Trades, PF, DD, WR, Expectancy
- Robust: pass/fail, Monte P95 DD, WFA OOS pass
- 1-3 “Lessons learned”

