# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-008 — non-repaint audit

Verdict: `PASS` for the frozen tick-exact event contract.

The standard bar scan found no `CopyBuffer`, `CopyRates`, `CopyTime`, `iOpen`,
`iHigh`, `iLow`, or `iClose` call and no bar-zero decision path. Closed-bar alignment
is therefore not applicable: this EA consumes a compile-time direction that was
calculated source-side only from CME 6E records with `ts_recv < T+60 seconds`.

The executable entry path requires `tick.time_msc >= event_server_msc + 60000`; exit
requires `tick.time_msc >= event_server_msc + 120000`. No current/future EURUSD price
is present in the source table, no score magnitude is exposed, and no threshold,
session, SL/TP, trailing, price-momentum, or alternate-horizon input exists. The exact
reverse comparator changes direction only.

PASS is engineering evidence only. It does not establish profitability or promotion
readiness.

