# LEAD NOTE R13 for EVAL-AUDIT (2026-09-21 18:47Z) — W0, before W1

The Lead viewed `rv/694313a3_9.54a.png`.
- The golden Asia box (02:00–09:10, about 1.2815–1.2837) is tagged **MISS**.
- Yet v1 draws a dashed BOX from 02:00 to about 07:45 at about 1.2812–1.2837. By eye, those are the same edges and the same episode.

Either the engine box fails for a real reason, or the ruler is misreading the engine's containment window. Example of the second case: `meta_build_end` recorded at the *proposal* bar rather than the last bar before the break. That would make the engine window tiny and IoU < 0.5 even when the box is right.

**W0, ≤ 30 min:**
1. For 9.54a, print for the golden box and every engine BOX-family object overlapping it:
   - the route;
   - `t_birth`;
   - `meta_build_start/end` (in minutes);
   - `break_bar`;
   - the drawn `t0/t1`;
   - the edges;
   - the eval_v2 route used (containment or coverage);
   - true IoU;
   - the overlap coefficient;
   - the edge deltas;
   - the final verdict, with the reason.
2. Check the semantics. Does the engine's `meta_build_end` mean what golden `build_end` means (the last bar before the first decisive close outside)? Check each box route: pullback_end, cluster_range, congestion_scan, asia/RANGE_OPEN, CONTEXT_RANGE.
3. Count across all 198 panels: engine BOX objects whose `meta_build_end` falls before their own `break_bar` by more than 30 min. For each of those, how many golden boxes would match if the window were `build_start..break_bar`?
4. If the conversion is inconsistent, **do not change the ruler.** Write the finding and the proposed conversion rule in `evalcheck/W0_BOX_WINDOW.md`. The Lead rules, and only then E1/E2 re-run and a new hash follow.

Then continue with W1.

---
- 18:52Z Correction (Lead): the header time "18:47Z" is wrong. This note was written at 18:44:47Z (file mtime, system clock). The Lead estimated instead of reading the clock. See Ruling 14 §14.1.
