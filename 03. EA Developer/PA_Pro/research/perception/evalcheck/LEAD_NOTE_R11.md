# LEAD NOTE R11 for EVAL-AUDIT (2026-09-21 17:35Z)

FUNNEL, the route diagnostic and the renders are good and useful: the Lead found two engine defects from the renders alone. Read `LEAD_RULINGS.md` **Ruling 11** first. Your changes, in order, before items 4–7 of mandate 2:

1. **§11.1 BOX rule.**
   - Match = true containment IoU ≥ 0.5, plus both edges within tol.
   - Remove the drawn-span coverage fallback, except for a side with no containment window at all; count those uses.
   - Add the diagnostic column **located** (overlap coefficient ≥ 0.5, plus edges). It is never a match.
2. **§11.3 Line sigma.** Repaired lines go to σ = 2.0 p (was 1.5), per LINE-LAB L1. Keep the |slope| · 10 min term.
   - Add "trusted-subset recall" for PATTERN_LINE. Tier A is the 44 ids in `linelab/LINE_YARDSTICK_AUDIT.md` §(b).
3. **Re-run E1/E2** on the changed ruler, plus `test_ruler.py`, with a new known-answer case for the §11.1 disjoint-episode rejection (9.40c-style).
   - Publish the new ruler hash in EVAL_AUDIT.md (addendum) and EVAL_LOG.md.
   - Re-run the full 198-panel bridge for v0 and the current v1, and add the `located` column.
4. **§11.2 Prefix-consistent funnel rule for candidates** (exact definitions in the ruling).
   - Re-run FUNNEL under it for v0 and v1: oracle ceilings, the taxonomy, and labels.
   - Say how many BOX "proposed_wrong_geometry" rows were really prefix artefacts.
5. **Renders:**
   - Tag every engine object with its type and short id (e.g. `BOX#3`, `RANGE_OPEN#1`, `SQUEEZE#2`), and add a legend.
   - Also write a flat copy to `evalcheck/rv/<hash8>_<panel>.png`. The Lead's viewer cannot reach `renders/<hash>/` because it is one folder too deep.
   - Re-render the 12 QA panels for the current v1 after each engine hash change you see.
6. **Small market clean-up** while you add D35 in `research/market/DEVIATIONS.md`: under D33, add one line.
   - The text: "Verification date above is the local date; the UTC time was 2026-09-21 ~17:18Z (Lead note, R11)."
   - The Lead authorises this one line; do not change anything else there.

Walls unchanged. Log every step in EVAL_LOG.md with clock times.
