# G1 — visual QA checklist (12 snapshots)

For each snapshot, verify ALL of the following before the screen runs.
Any FAIL requires a spec/detector note before proceeding.

- [ ] signal bar is a pullback INTO the zone (price reaches the proximal
      edge), not a thrust away from it
- [ ] **not a chase**: the LIMIT order sits AT the zone edge
      (long just below z.hi / short just above z.lo), at or beyond the
      signal close — never ~10+ pips past the band
- [ ] **zone is salient (at most 1 or 2 bands near price)**: the
      triggering zone is visibly the dominant band; the plot does not
      show a stack of 4+ near-price zones all "armed"
- [ ] the zone has visible prior respect (touches/reactions) — it is a
      level the chart itself makes obvious
- [ ] HTF trend agrees with the trade side (H1/H4 structure in pane B)
- [ ] **stop at real structure**: SL rung reaches beyond the deeper of
      (zone far edge, pullback extreme); `inv` line sits behind it
- [ ] room to the opposing zone is at least ~2R (opposing band, if any,
      is visibly far)
- [ ] signal bar closes inside session (EU/US), bar range not degenerate
- [ ] TP target (tp_mult x S) lies on the trade side, beyond the edge
- [ ] dedupe: no two signals on the same zone within 12 bars
