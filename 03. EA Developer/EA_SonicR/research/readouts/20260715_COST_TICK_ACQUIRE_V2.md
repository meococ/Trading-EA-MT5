# Cost/tick acquire V2 — Track A

Date: 2026-07-15
Status: `SINGLE_DAY_OR_SHALLOW_HISTORY_DIAGNOSTIC_ONLY`
Research freeze eligible: **False**
Receipt SHA: `80EF7C186468219D4DDB93BCB7956BD0E1F75B00877B6BE59C9E2493C91B4E70`
Table SHA: `5E92CC645139741288D12D4105DA6DFD6C819437CE8B24A710BD266D16BE32BB`

## Verdict

- Union quote calendar days: **2** (need 90) → `['2026-07-13', '2026-07-14']`
- MT5 history max days/symbol: **2**
- QFSI disk days: **1**
- Sessions covered (MT5): `['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF']`
- Commission merged: `{'BTCUSD': 3, 'EURUSD': 2}`
- Gaps: quote_days=2/90, EURUSD_comm=2/30, USDJPY_comm=0/30, slip≈0/100+_MISSING_NE_0
- RR2 re-stress: `NOT_RUN_SURFACE_NOT_RESEARCH_GRADE`

## Live deals (opportunistic)

- OK: `True` login=`26451822` server=`FivePercentOnline-Real`
- n_deals=`11` comm=`{'BTCUSD': 3, 'EURUSD': 2}`
- slip: `MISSING_NE_0` (MISSING ≠ 0)

## MT5 day-chunk + anchor sample

- Server/login: `FivePercentOnline-Real` / `26451822`
- OK: `True` error=`None` max_days=`60`

- **USDJPY**: days=2 ticks=327579 usd/lot p50=0.0 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T17:55:02+00:00→2026-07-14T19:24:14+00:00
- **EURUSD**: days=2 ticks=303642 usd/lot p50=0.0 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T00:05:00+00:00→2026-07-14T20:55:03+00:00
- **GBPUSD**: days=2 ticks=403384 usd/lot p50=0.9999999999843466 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T17:55:02+00:00→2026-07-14T19:07:07+00:00
- **XAUUSD**: days=2 ticks=1701455 usd/lot p50=0.4600000000000364 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T17:55:02+00:00→2026-07-14T18:11:07+00:00
- **AUDUSD**: days=2 ticks=397144 usd/lot p50=0.0 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T17:55:02+00:00→2026-07-14T19:15:59+00:00
- **NZDUSD**: days=2 ticks=320126 usd/lot p50=4.0000000000039995 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T17:55:02+00:00→2026-07-14T19:24:02+00:00
- **USDCAD**: days=2 ticks=370194 usd/lot p50=2.8432111226447554 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T17:55:02+00:00→2026-07-14T18:55:54+00:00
- **USDCHF**: days=2 ticks=338066 usd/lot p50=6.179018524696858 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T17:55:02+00:00→2026-07-14T19:38:03+00:00
- **EURJPY**: days=2 ticks=733320 usd/lot p50=6.782921836072615 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T17:55:02+00:00→2026-07-14T18:30:13+00:00
- **GBPJPY**: days=2 ticks=841948 usd/lot p50=14.18273529465936 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T17:55:02+00:00→2026-07-14T18:23:53+00:00
- **BTCUSD**: days=2 ticks=1423737 usd/lot p50=2.8000000000029104 sessions=['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF'] anchors={} window=2026-07-13T17:55:02+00:00→2026-07-14T18:15:42+00:00

## Policy

- Do **not** invent commission/slip.
- Do **not** claim research-grade freeze unless freeze_eligible.
- Keep Real QFSI accumulate as parallel hygiene (not stall).

## Artifacts

- `03. EA Developer/EA_SonicR/research/preflight/20260715_COST_TICK_ACQUIRE_V2.json`
- `03. EA Developer/EA_SonicR/research/preflight/20260715_COST_SURFACE_SESSION_HOUR_TABLE_V2.json`
- `03. EA Developer/EA_SonicR/research/readouts/20260715_COST_TICK_ACQUIRE_V2_COVERAGE_PROOF.md`
- `03. EA Developer/EA_SonicR/research/readouts/20260715_COST_TICK_ACQUIRE_V2_REMAINING_GAP.md`

