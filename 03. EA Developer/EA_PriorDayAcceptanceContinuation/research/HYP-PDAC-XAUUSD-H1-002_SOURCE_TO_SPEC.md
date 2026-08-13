# HYP-PDAC-XAUUSD-H1-002 source-to-spec matrix

| Frozen rule | MQL5 implementation |
|---|---|
| Parent HYP001 two-close event unchanged | chronological `IsRawEvent` scan on closed H1 rates |
| First event per broker date | signal only when the first raw-event index equals the latest closed bar |
| Exact next-bar first tick | `availability_time - decision_time == 3600` plus initialized current-bar clock |
| Attach/restart fail-closed | `OnInit` seeds `g_last_bar_open`; same-day rescan blocks later duplicate |
| Friday operational boundary | entry and flatten block only at Friday UTC hour >=20 |
| Structural stop | prior boundary minus/plus 0.25 prior-day range |
| Target/hold/risk | 1.50R, eight H1 bars, 0.25% equity via `OrderCalcProfit` |
| DQ provenance | read-only M1/M5 `DATA_EPOCH_D0_SERIES_PROOF` |

No bar-zero signal or indicator read is used.
