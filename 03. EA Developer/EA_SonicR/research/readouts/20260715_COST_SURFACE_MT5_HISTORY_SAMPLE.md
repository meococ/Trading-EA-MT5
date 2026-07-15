# Cost surface — MT5 history + QFSI sample (Track A)

Date: 2026-07-15
Status: `SINGLE_DAY_OR_SHALLOW_HISTORY_DIAGNOSTIC_ONLY`
Research freeze eligible: **False**
Receipt SHA: `F2A1F12EFD38E05B82D7B31CB871BD97993ED868C7F9FD3834BB02DDF488002E`
Table SHA: `D12519B37A0CB9E24D8141A4099EFCA6C4E1068141CD3861194B2ADD68A9EE48`

## Verdict

- Union quote calendar days: **2** (need 90)
- MT5 history max days/symbol: **2**
- QFSI disk days: **1**
- Gaps: quote_days=2/90, EURUSD_comm=2/30, USDJPY_comm=0/30, slip≈0/100+
- RR2 re-stress under session surface: `NOT_RUN_SURFACE_NOT_RESEARCH_GRADE`

## MT5 opportunistic sample

- Server/login: `FivePercentOnline-Real` / `26451822`
- OK: `True` error=`None`

- **USDJPY**: days=2 ticks=317536 usd/lot p50=0.0 p90=0.6166026427618709 window=2026-07-13T17:31:05+00:00→2026-07-14T18:18:49+00:00
- **EURUSD**: days=2 ticks=295951 usd/lot p50=0.0 p90=1.000000000006551 window=2026-07-13T00:05:00+00:00→2026-07-14T19:24:48+00:00
- **GBPUSD**: days=2 ticks=392591 usd/lot p50=0.9999999999843466 p90=1.9999999999908977 window=2026-07-13T17:31:05+00:00→2026-07-14T18:16:42+00:00
- **XAUUSD**: days=2 ticks=1692514 usd/lot p50=0.4600000000000364 p90=0.5100000000002183 window=2026-07-13T17:31:05+00:00→2026-07-14T17:41:52+00:00

## Policy

- Do **not** invent commission/slip.
- Do **not** claim research-grade multi-year cost surface unless freeze_eligible.
- Keep Real QFSI accumulate as parallel hygiene (not stall).

## Artifacts

- `03. EA Developer/EA_SonicR/research/preflight/20260715_COST_SURFACE_MT5_HISTORY_SAMPLE.json`
- `03. EA Developer/EA_SonicR/research/preflight/20260715_COST_SURFACE_SESSION_HOUR_TABLE_V1.json`
- `03. EA Developer/EA_SonicR/research/readouts/20260715_COST_SURFACE_COVERAGE_PROOF.md`

