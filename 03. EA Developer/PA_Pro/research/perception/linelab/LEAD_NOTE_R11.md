# LEAD NOTE R11 for LINE-LAB (2026-09-21 17:35Z)

L1 and L2 are accepted. This is the best line analysis the program has had: the yardstick contract is measured, 44 labels are named as suspect, and the anatomy tells the builder what to do.

1. **Ruler.** Your L1 sets repaired-line σ = 2.0 p (Lead Ruling 11 §11.3). EVAL-AUDIT is implementing it with a new ruler hash.
   - Until it lands, report L3 under the current ruler.
   - When it lands, re-run L3 and the v0/v1 baselines under the new hash, in the same table.
   - Report trusted-subset recall (n = 141) as well as all-184 recall.
2. **Market facts** (DR-MARKET FINAL v2, both stable):
   - A 3rd-or-later touch on a real pivot line bounces +7–8 pt more often than placebo. So the 3rd touch must not end a line; the line lives through it.
   - Level premium is ≈ 0 after about 5 h without a touch. Use that as a stale-line retirement bound (48–96 bars), and write it into L4.
3. **L3 debugging.** "0 lines/panel, 108 candidates evaluated, no births" means the veto is somewhere in the trigger or the gates.
   - Instrument it, fix it, and log the veto histogram in ROUND_1.md.
   - Keep the freshness trigger (L2 §5: the draw moment is the strongest signal).
