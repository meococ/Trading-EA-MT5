# Frozen preregistration - HYP-VRAS-EURUSD-M5-003

Status: FROZEN PRE-OUTCOME on 2026-07-22.

HYP-003 is the final mechanical successor to HYP-001/002. It preserves every
signal, threshold, risk, session, cost, news and data rule. Relative to HYP-001
it accepts boolean-successful `OrderCheck()` preflights for entry/exit. Relative
to HYP-002 it changes only the internal identity guard to ID 003/magic 5600743;
HYP-002 reached no market data because OnInit rejected its stale identity.

Frozen execution: EURUSD M5 Model 0, 2019.01.03-2022.12.31, deposit 100,000
USD, leverage 1:100, current spread, lifecycle-v3. Primary is tick-volume
Welford VWAP/SD with London-local anchor; ADX 25/19/dwell6; warmup15; SD floor
0.30 ATR; Range RSI 25/75 at 2SD; Trend confirmed five-bar AVWAP + M15 bias,
1.80R; risk 0.25%; max spread 1.20 pip; cost K=8; 3 trades/day; daily loss
1.50%; account DD 6%; 20-bar hold; news +/-45m; broker UTC+2 winter/US DST.

Acceptance: 13 tests PASS, compile 0/0, exact-source non-repaint 0 findings,
sidecars reconcile, >=350 trades, 2-5 trades/elapsed week, diagnostic PF>=1.30,
DD<=6%. Cost/news provenance remains unverified, so promotion/live is forbidden
regardless of metrics. Exactly one primary run; no optimizer, sensitivity arm,
filter relaxation, time veto or 2023+ access.
