---
name: alpha-monte-carlo
description: Run AlphaFactory Monte Carlo simulation on MT5 report to estimate worst-case drawdown (P95) and path dependency. Use when deciding risk sizing against the frozen prereg budget.
---

## Lệnh chạy
- `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" monte -Report "<PATH_TO_REPORT.html>"`

## Tham số mặc định
- `--sims 1000`
- `--equity` (auto-detect từ report hoặc 10000)

## Output
- `{run_folder}/monte_carlo/monte_carlo_results.json`
- Metric chốt: `max_drawdown_pct.p95`

## Cách đọc

P95 DD = ngưỡng mà 95% permutation không vượt. So với **budget DD đã freeze trong prereg/acceptance_contract**, không với trần 8%/18%/20% của skill khác.

Nếu P95 vượt budget đã freeze: giảm risk/trade hoặc exposure trước khi đổi logic. Không nới budget sau khi đã thấy outcome.
