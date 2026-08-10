# HYP-STBS-XAUUSD-M15-020 V6/V7 bounded diff proof

V7 is the fresh economic implementation identity required after terminal HYP019 froze the malformed cost-manifest hash. There was no HYP019 MT5 attempt or economic outcome.

The focused normalization test maps V7 back to V6 using only these substitutions:

- version `7.00` to `6.00` and the descriptive label;
- EA name `EA_SupertrendBurstScalperTradeV7` to V6;
- hypothesis HYP020 to HYP019;
- variant V7 to V6;
- magic `5604120` to `5604119`.

After those substitutions, the MQL source is byte-identical to V6. No signal, Supertrend/ATR formula, geometry, position sizing, margin, session, design window, order gateway, execution FSM, persistence, exit, telemetry reconciliation or lifecycle rule changed.
