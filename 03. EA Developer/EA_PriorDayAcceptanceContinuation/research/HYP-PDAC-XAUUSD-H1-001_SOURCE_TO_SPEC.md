# HYP-PDAC-XAUUSD-H1-001 source-to-spec matrix

| Frozen rule | MQL5 implementation |
|---|---|
| Completed native H1 bars only | `CopyRates(PERIOD_H1, 1, 72, ...)` |
| Prior nonempty broker trading day | adjacent `DateKey` groups in chronological closed rates |
| Reference day has 20–24 valid H1 bars | strict `prior_count` and `ValidRate` checks |
| First two-close acceptance only | chronological `IsRawEvent` scan; signal only when first event index is latest closed bar |
| LONG/SHORT strict inverse | exact close inequalities around prior high/low; equality never signals |
| Exact-next decision | current H1 open minus decision close must equal 3,600 seconds |
| Structural stop | prior boundary minus/plus 0.25 prior-day range |
| Target/hold/risk | 1.50R, eight H1 bars, 0.25% equity via `OrderCalcProfit` |
| Broker safety | tick/stops/margin/volume checks, one symbol position, no pyramid |
| Data-quality provenance | read-only M1/M5 `DATA_EPOCH_D0_SERIES_PROOF` in `OnInit` |

No bar-zero signal or indicator value is read. The first-event rescan makes the
daily consumption rule deterministic after an EA restart.
