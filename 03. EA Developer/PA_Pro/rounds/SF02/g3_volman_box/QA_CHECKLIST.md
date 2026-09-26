# G3 — visual QA checklist (12 snapshots)

For each snapshot, verify ALL of the following before the screen runs.
Any FAIL requires a spec/detector note before proceeding.

- [ ] **box visibly tight**: the 12-bar box is an obvious compression —
      clearly narrower than the surrounding bar ranges (percentile test
      made visible), not a spike-and-fade cluster
- [ ] box bodies are small (mean |c-o| <= 0.5xATR M5) — no trend bars
      inside the box
- [ ] **zone is salient (at most 1 or 2 bands near price)**: the zone the
      box presses against is the dominant band, not one of many
- [ ] the box presses against the zone's near edge (box edge within
      ~0.5xATR of the zone edge)
- [ ] the break bar closes BEYOND the zone's far edge, with the HTF trend
      (H4 structure agrees)
- [ ] **not a chase**: the STOP order sits ~1 pip beyond the box edge —
      the box is tight, so the stop sits close to structure, not far
      behind price
- [ ] **stop at real structure**: SL rung covers the far side of the box;
      `inv` line sits at the box's far edge
- [ ] signal bar in session (EU/US); no weekend adjacency
- [ ] TP (2xS) lies on the trade side beyond the break
- [ ] dedupe: one signal per zone per 12 bars
