---
name: alpha-walk-forward
description: Run AlphaFactory walk-forward analysis (WFA) on an MT5 report and interpret IS/OOS stability. Use when checking overfitting and robustness across rolling windows.
---

## Lệnh chạy
- `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" wfa -Report "<PATH_TO_REPORT.html>"`

## Tham số mặc định
- `--windows 5` (chia thành 5 cửa sổ rolling)
- `--ratio 0.7` (70% IS, 30% OOS)

## Output
- File: `{run_folder}/walk_forward/wfa_results.json`
- Gồm:
  - `windows[]` — mỗi window có IS metrics + OOS metrics + `degradation_pct` + `oos_profitable`
  - `summary` — `avg_is_pf`, `avg_oos_pf`, `avg_degradation_pct`, `oos_profitable_ratio`, `efficiency_ratio`
  - `verdict` — `{level, emoji, message, recommendation}`

## Cách đọc kết quả

### Metrics quan trọng nhất (đọc theo thứ tự)
1. **`efficiency_ratio`** (OOS/IS): chiến lược generalize tốt không?
2. **`oos_profitable_ratio`**: bao nhiêu % window OOS có lãi?
3. **`avg_degradation_pct`**: IS → OOS sụt bao nhiêu %?

### Bảng đánh giá

| Metric | EXCELLENT | GOOD | WARNING | POOR |
|--------|-----------|------|---------|------|
| `efficiency_ratio` | >= 0.80 | 0.60-0.79 | 0.40-0.59 | < 0.40 |
| `oos_profitable_ratio` | >= 80% | 60-79% | 40-59% | < 40% |
| `avg_degradation_pct` | < 10% | 10-20% | 20-40% | > 40% |

### Verdict levels
- **EXCELLENT** (efficiency >= 0.8 AND oos_ratio >= 0.8): generalize tốt, tin cậy
- **GOOD** (efficiency >= 0.6 AND oos_ratio >= 0.6): chấp nhận được, theo dõi OOS
- **WARNING** (efficiency >= 0.4 AND oos_ratio >= 0.4): yếu, cần review
- **POOR** (else): overfit hoặc regime-dependent, KHÔNG trade

## Quy tắc quyết định
- OOS pass rate >= 60% mới coi là ổn.
- Nếu OOS fail nhưng IS tốt → dấu hiệu overfit hoặc regime-dependence.
- Nếu 1-2 window OOS fail mà còn lại OK → kiểm tra window đó rơi vào năm nào (regime shock?).
- `avg_degradation_pct` > 30% → edge không robust, dù OOS vẫn dương.

## PROP_READY gate
- `efficiency_ratio` >= 0.60
- `oos_profitable_ratio` >= 60%
