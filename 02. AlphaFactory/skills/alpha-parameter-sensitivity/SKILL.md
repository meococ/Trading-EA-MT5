---
name: alpha-parameter-sensitivity
description: Run AlphaFactory parameter sensitivity analysis and optionally heatmap mode. Use when you need to evaluate parameter stability/fragility and detect curve-fitting sensitivity around a chosen parameter.
---

## Lệnh chạy

### 1D Sensitivity (1 parameter)
- `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" param -Report "<PATH_TO_REPORT.html>"`

### 2D Heatmap (2 parameters)
- `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" param "heatmap" -Report "<PATH_TO_REPORT.html>"`

## Cách dùng
- Chỉ làm **sau khi** strategy có edge baseline (PF > 1.1, trades đủ).
- Mục đích: parameter hiện tại có nằm trong "vùng ổn định" hay "đỉnh nhọn"?

## Output — 1D Sensitivity
- File: `{run_folder}/param_analysis/sensitivity_results.json`
- Variations: **[-30%, -20%, -10%, 0%, +10%, +20%, +30%]** (7 levels)
- Gồm:
  - `results[]` — mỗi variation: `{variation, variation_pct, profit_factor, profitable}`
  - `statistics` — `{pf_mean, pf_std, pf_min, pf_max, pf_range, profitable_variations, profitable_pct}`
  - `stability_score` (0-100)
  - `verdict` — `{level, emoji, message, recommendation}`

### Bảng đánh giá 1D

| Level | Điều kiện | Ý nghĩa |
|-------|-----------|---------|
| STABLE | score >= 70 AND profitable >= 80% | Parameter robust, ít risk overfit |
| MODERATE | score >= 50 AND profitable >= 60% | Chấp nhận được, dùng conservative values |
| SENSITIVE | score >= 30 AND profitable >= 40% | Nhạy cảm, cần review kỹ |
| UNSTABLE | else | Overfit risk cao, parameter quá fragile |

## Output — 2D Heatmap
- File: `{run_folder}/param_analysis/heatmap_results.json`
- Chart: `{run_folder}/param_analysis/param_heatmap.png`
- Grid: **7x7** (49 combinations), 20 samples/cell với noise
- Gồm:
  - `param1`, `param2`: tên 2 parameters
  - `profitable_combinations`, `profitable_pct`
  - `optimal` — `{param1_variation, param2_variation, profit_factor}`
  - **`has_islands`** — boolean, RED FLAG nếu `true`

### Đọc heatmap
- **Contiguous green region** (has_islands=false): parameter stable, vùng profitable rộng → GOOD
- **Scattered green spots** (has_islands=true): "đảo" lợi nhuận rải rác → OVERFIT SIGNAL
- Optimal point nằm ở rìa grid? → có thể chưa tìm đúng vùng, cần mở rộng range

## Quy tắc quyết định
- `stability_score` >= 50 AND `profitable_pct` >= 60%: chấp nhận được
- Sensitivity quá nhọn (chỉ 1 vùng hẹp pass) → rủi ro overfit cao
- Nếu `pf_std` < 0.02: rất ổn định
- Nếu `profitable_pct` = 100%: robust
- `has_islands` = true trên heatmap → RED FLAG, cần simplify strategy

## PROP_READY gate
- `stability_score` >= 50
- `profitable_pct` >= 60%
- Heatmap: `has_islands` = false (nếu chạy 2D)
