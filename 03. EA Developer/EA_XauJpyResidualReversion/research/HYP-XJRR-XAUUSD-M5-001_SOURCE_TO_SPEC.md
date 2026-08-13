# HYP-XJRR-XAUUSD-M5-001 source-to-spec matrix

| Frozen source rule | Required MQL5 behavior |
|---|---|
| Exact XAUUSD/USDJPY M5 join | Merge closed rates by identical server timestamp; no forward-fill |
| Prior 288 paired returns | Compute each beta/sigma from bars before its own return |
| Prior/current z re-entry | Recompute both causal z values; equality only arms |
| First raw event/server date | Consume before availability, overlap, Friday or geometry checks |
| 12 joined-bar lockout | Reconstruct and decrement by synchronized closed bars, including across dates |
| Exact next availability | Require current XAU and USDJPY bar open at decision +300 seconds |
| Friday boundary | No entry and flatten from Friday 20:00 UTC |
| Residual exit | LONG z>=0; SHORT z<=0 on a completed bar; no same-tick reversal |
| Risk/hold | ATR14 x1.25 stop, 0.25% equity risk, max 12 completed M5 bars |

The source cadence is explicitly an upper bound. Runtime summary must expose raw
signals, sides, exact-next rejects, overlap/reconstruction skips, geometry/order
rejects, entries and closes without printing per-bar spam.
