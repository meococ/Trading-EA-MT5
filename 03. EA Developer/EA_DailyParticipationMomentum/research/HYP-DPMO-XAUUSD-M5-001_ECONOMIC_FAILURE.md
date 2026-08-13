# HYP-DPMO-XAUUSD-M5-001 — economic baseline failure

Verdict: `KILL_BASE_PF_EXPECTANCY_FAIL_CADENCE_PASS`

The unchanged source-passed DPMO mapping completed its verified FivePercent
XAUUSD M5 Model-0 baseline. Engineering, source parity, history-quality and
cadence gates passed; the economic thesis failed materially after tester spread
and commission.

## Verified result

- run: `20260811_124123`
- history quality: `99%`; bars/ticks: `351303 / 135208676`
- source identity: raw `599`, LONG `301`, SHORT `298`
- completed trades: `597`; two broker invalid-stop rejections
- elapsed cadence: `2.288609` trades/week — PASS `2..5`
- PF: `0.7978167955` — FAIL `>1.30`
- expectancy: `-$9.654238/trade` — FAIL `>0`
- net profit: `-$5,763.58`
- win rate: `42.0436%`
- maximum relative drawdown: `6.0204%` — PASS `<=8%`
- every weekday was negative with PF `0.72..0.86`; this is diagnostic only and
  does not authorize weekday/session/direction deletion.

## Evidence

- run manifest SHA256:
  `2839E879B8F39EFA33D1E760D45EEC0FB9BF6603513E1C3A65D84B4E29D23A48`
- report SHA256:
  `3E197509BD86452936481BBCC1E0C42769EDB789EEE7CCA746488810A52652F9`
- journal SHA256:
  `D1F9BDD2692117E58F19DA0BF522AECC3A68D5673864AB1A60144432D7643486`
- enhanced summary SHA256:
  `534605054FFEDC7D78B66FB705413B81CE7FB75A410D8060E8EBDDA765A6B251`
- non-repaint audit: PASS, zero findings.
- runtime summary: `runtime_failed=false`, `clock_rejects=0`, exact raw/source
  counts, and no journal truncation.

An earlier engineering run `20260811_123745` completed MT5 but failed before
analysis because the EA's D0 provenance line omitted fields required by the
AlphaFactory parser. The mapping and outcomes were not used to change trading
logic; only the log schema was repaired, recompiled and re-audited.

## Failure radius and prohibition

This kills the exact daily activity-above-prior20-median momentum continuation
with the frozen 12-bar structural stop, 0.20 ATR buffer, 1.5R target and 20:00
UTC exit on XAUUSD M5, 2018–2022. It does not establish that every daily
participation mechanism lacks edge.

No median/lookback threshold, inverse direction, weekday/session deletion,
ATR/stop/target/hold/risk change or subgroup rescue is permitted under this ID.
Optimization, validation, holdout, cost-stress promotion, paper and live remain
closed. The next experiment must use a materially fresh information mechanism.

