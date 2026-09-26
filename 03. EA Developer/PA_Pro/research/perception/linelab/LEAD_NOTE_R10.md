# LEAD NOTE R10 for LINE-LAB (2026-09-21 17:19Z)

1. **`evalcheck/eval_v2.py` is now the official ruler** (Lead Ruling 10). Report every L3 number under eval_v2 first, with `eval.py` as the legacy column.
   - The frozen ruler hashes are in Ruling 10. Import them; never edit them.
2. **Your L1 decides the line tolerance.** `evalcheck/common.py` `prec_sigmas` gives repaired lines 1.5 p; you already spotted this.
   - In `LINE_YARDSTICK_AUDIT.md`, add a section "Recommended sigma" with the measured endpoint residual distribution per repair stratum: p50, p80 and p90, in pips and in ABR.
   - EVAL-AUDIT turns it into a proposal, and the Lead rules. Do not tune L3 against a sigma the labels cannot support.
3. **Baseline you must beat, 198 TUNE panels, eval_v2:** PATTERN_LINE recall v0 0.10 (18/186), v1 0.09 (16/186). Precision is ≤ 0.03 for both.
