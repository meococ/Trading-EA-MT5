# HYP-NYOD-XAUUSD-M15-001 source-to-spec matrix

| Frozen rule | Source implementation |
|---|---|
| Closed M15 drive bar and exact next open | `CopyRates(...,1,10)` plus `availability-decision==900` |
| New York 08:15 drive / 08:30 availability | broker Europe-DST → UTC → US-DST New York conversion |
| Prior two-hour range | strict extrema over the eight bars preceding the drive |
| Prior ATR14 | native `iATR`, `CopyBuffer(...,shift=2)` |
| Drive geometry | TR >=1.00 ATR, body/bar-range >=0.60, close-location >=0.75 |
| Continuation | close strictly beyond prior range in drive direction |
| Entry/stop/target | exact next-bar market; drive extreme ±0.15 ATR; 1.50R |
| Hold/risk | six completed M15 bars; 0.25% equity via `OrderCalcProfit` |
| Safety | one symbol position, broker geometry/margin checks, daily/account locks, Friday guard |
| Data-quality provenance | read-only M1/M5 `DATA_EPOCH_D0_SERIES_PROOF` during `OnInit` |

The implementation contains no bar-zero signal/indicator reads. Compile result:
0 errors, 0 warnings. Static non-repaint audit: PASS.
