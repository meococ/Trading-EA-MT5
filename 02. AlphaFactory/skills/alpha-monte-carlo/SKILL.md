---
name: alpha-monte-carlo
description: Run AlphaFactory Monte Carlo simulation on MT5 report to estimate worst-case drawdown (P95) and path dependency. Use when deciding risk sizing and whether DD is acceptable under random trade order permutations.
---

## Lệnh chạy
- `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" monte -Report "<PATH_TO_REPORT.html>"`

## Tham số mặc định
- `--sims 1000` (1000 random permutations)
- `--equity` (auto-detect từ report hoặc 10000)

## Output
- File: `{run_folder}/monte_carlo/monte_carlo_results.json`
- Gồm:
  - `final_equity` — `{mean, std, median, p5, p25, p75, p95, min, max}`
  - `max_drawdown_pct` — `{mean, median, p50, p75, p95, p99, max}` ← **CRITICAL**
  - `risk_of_ruin` — `{prob_lose_50pct, prob_lose_25pct, prob_breakeven}`
  - `worst_case` — `{worst_final_equity, worst_drawdown_pct, worst_equity_ever}`

## Cách đọc kết quả

### Metric quan trọng nhất: `max_drawdown_pct.p95`
P95 DD = DD xấu nhất mà 95% simulations không vượt quá. Đây là "worst-case thực tế".

### Bảng đánh giá P95 DD

| P95 DD | Level | Hành động |
|--------|-------|-----------|
| <= 8% | PROP_READY | Sẵn sàng prop/live |
| 8-15% | GOOD | Standard position sizing OK |
| 15-25% | CAUTION | Xem xét giảm risk/trade |
| 25-40% | WARNING | Giảm position size hoặc tighten filter |
| > 40% | CRITICAL | KHÔNG trade. Cần fix strategy trước |

### Risk of Ruin
- `prob_lose_50pct` < 1%: chấp nhận được
- `prob_lose_25pct` < 5%: theo dõi
- `prob_breakeven` < 10%: OK

### Hành động khi P95 DD quá cao
1. Giảm risk/trade (lot size)
2. Tighten session/spread/volatility filter
3. Giới hạn max trades/day
4. Review SL placement (quá rộng?)
5. Nếu vẫn > 30% sau tất cả → edge chưa đủ mạnh

## PROP_READY gate
- `max_drawdown_pct.p95` <= 8%
- `risk_of_ruin.prob_lose_50pct` < 1%
