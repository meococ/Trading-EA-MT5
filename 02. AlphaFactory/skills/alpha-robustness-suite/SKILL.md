---
name: alpha-robustness-suite
description: Run AlphaFactory professional robustness suite (7 tests) on an MT5 report and interpret pass/fail thresholds. Use when you need to validate robustness beyond PF/DD.
---

## Lệnh chạy
- `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" robust -Report "<PATH_TO_REPORT.html>"`

## Output
- File: `{run_folder}/robustness/robustness_results.json`
- Gồm `tests{}` (7 test objects) + `summary{passed, total, pass_rate, overall_verdict, recommendation}`

## 7 Tests chi tiết

### 1. Sample Size Validation
- Kiểm trades đủ chưa cho statistical significance
- >= 400: HIGH confidence (95%), 200-399: MODERATE (80%), 100-199: LOW (60%), <100: VERY LOW
- **PASS**: >= 200 trades

### 2. Noise Testing (thêm ±0.1% price noise)
- Thêm random noise vào giá, chạy 100 lần
- Đo `noisy_pf_mean`, `noisy_pf_min`, `degradation_pct`
- **PASS**: mean PF > 1.0 AND min PF > 0.9

### 3. Parameter Sensitivity (±10% Gaussian noise per trade)
- Biến đổi kết quả mỗi trade ±10%, chạy 100 lần
- Đo `pf_mean`, `pf_min`, `stability_score` (0-100)
- **PASS**: mean PF > 1.0 AND min PF > 0.8 AND stability > 50

### 4. Vs. Random Benchmark (1000 random strategies)
- So sánh strategy với 1000 chiến lược ngẫu nhiên
- Đo `percentile` (vị trí xếp hạng so với random)
- **PASS**: beats >= 95% random strategies
- **CRITICAL**: nếu FAIL → edge không tốt hơn random, DỪNG

### 5. Variance Testing (Bootstrap 95% CI)
- Bootstrap 1000 lần, tính 95% CI của PF
- Đo `ci_95_lower`, `ci_95_upper`
- **PASS**: CI lower > 1.0
- **CRITICAL**: nếu CI lower <= 1.0 → edge chưa statistically significant

### 6. Delayed Entry Testing (0.5% slippage impact)
- Giả lập execution delay: winner giảm, loser tăng
- Đo `degradation_pct`, `delayed_pf_mean`, `delayed_pf_min`
- **PASS**: degradation < 10% AND avg PF > 1.0

### 7. Vs. Shifted Bars (±5, ±15 min shifts)
- Dịch thời gian entry ±5, ±15 phút
- Đo `avg_shifted_pf`, `min_shifted_pf`, `degradation_pct`
- **PASS**: min PF > 1.0 AND degradation < 15%

## Bảng tổng hợp verdict

| Pass Rate | Level | Hành động |
|-----------|-------|-----------|
| 7/7 (100%) | EXCELLENT | Sẵn sàng promote |
| 5-6/7 (71-86%) | GOOD | Review test fail, có thể chấp nhận |
| 4/7 (57%) | MODERATE | Cần fix issues trước khi trade |
| < 4/7 | POOR | KHÔNG trade. Strategy chưa robust |

## Quy tắc quyết định
- PASS rate >= 60% mới coi là có dấu hiệu robust.
- **"Vs Random" FAIL hoặc "Variance CI lower <= 1.0" FAIL** → edge KHÔNG đáng tin. Ưu tiên fix trước mọi thứ.
- Sample size thấp → chỉ tham khảo, cần tăng sample (multi-symbol/longer period).
- Noise/Shift fail → strategy quá nhạy cảm với timing/execution → review entry/exit logic.

## PROP_READY gate
- Pass rate >= 60% (4/7)
- Bắt buộc PASS: "Vs Random" + "Variance CI"
