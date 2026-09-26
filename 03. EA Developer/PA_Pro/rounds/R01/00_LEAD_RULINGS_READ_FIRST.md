# LEAD RULINGS FOR R01 — READ BEFORE WRITING PHYSICS_PREREG.md / FREEZE.json (2026-09-20 21:57 VN)

ZONE-1 is DONE: research/zones/REVIEW_ZONE1.md = VERDICT: PASS (after one FAIL/fix cycle); 50 tests pass.

1. EVENT POPULATION. The primary bake-off population is the ARMED zone population exactly as
   research/zones/SHORTLIST.md section 4 pre-declares (zones within +-2 x ATR14(H1) of the close,
   not currently broken, at most the chart-hygiene cap). The "all intact live zones" population of
   PHYSICS_PREREG_DRAFT.md becomes a pre-declared SENSITIVITY view (reported, never used to select).
2. CANDIDATES. All 6 SHORTLIST generators at their frozen defaults; line1_cluster is the baseline.
   Winner rule, power floors, BH over 6 x 2 endpoints, +5pp threshold, +2.0pp materiality vs the
   baseline and the tie-breaks exactly as SHORTLIST section 4. A candidate below its power floor is
   UNDERPOWERED (not a loss); profile_va is expected to be underpowered — do not change it.
3. Known residual accepted: ZoneGen.state_at replays from born_idx while the pass starts at
   created_idx (cosmetic, prefix invariance holds, no look-ahead). Pin the current code SHAs.
4. Everything else from the R01 fire prompt stands (FREEZE.json before any outcome, DESIGN only,
   core 4 symbols, M5, pa_slots, one ledger trial per generator, reviewer, then Phase C).
