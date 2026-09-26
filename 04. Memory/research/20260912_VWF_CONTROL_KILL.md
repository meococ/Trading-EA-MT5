# 2026-09-12 — HYP-VWF-XAU-M5-001 control screen: KILL

## Verdict

`HYP-VWF-XAU-M5-001` (EA_VwapFade, XAUUSD M5, session VWAP deviation fade)
→ **killed** at Model 0, registry row updated (screened→killed, validator
green). Second hypothesis to traverse the complete governed chain.

Run `20260912_030641` (governed, portable isolate, MetaQuotes-Demo):

| Metric | Value |
|---|---|
| Window | all-available; history 2004.06.11 → 2026.09.10 |
| Trades | 25,417 (~8.6/week — below 10–40 cadence band) |
| Report PF | 0.87; Net -7,645 USD; Max DD 76.8%; WR 43.8% |
| History Quality | 98% |
| Cost-bound PF | **0.50** @x1.0 / **0.38** @x1.5 / **0.29** @x2.0 |
| Monte Carlo p95 DD | 77.9% (limit 20) |
| Robustness pass rate | 14.3% |
| Overnight/weekend | **PASS** — 0/0 (Friday flatten + Mon–Thu session works) |
| Unified verdict | REVIEW — 9 FAIL / 2 BLOCKED / 3 PASS of 14 gates |

Disqualifying on economics under every stress tier. VWAP-fade has no positive
mean-reversion edge on XAUUSD M5 at this cost level. No post-hoc rescue.

## Cell-specific notes

- `SessionVwap` rewrote per-bar `iTime/iHigh/iLow/iClose/iTickVolume(i)` loop
  to a single `CopyRates(_Symbol,_Period,1,399,rates)` bulk read — identical
  bar set and math, required by the literal-shift non-repaint gate. Pattern
  for any future multi-bar-lookback EA: bulk-copy closed bars, index the
  array; never loop `iTime/i*` with a variable shift.
- Registry rows must be **pure ASCII**: PS5.1 `Get-Content` decodes
  no-BOM UTF-8 as ANSI, so a `—` byte-sequence hashes differently between
  Python (raw bytes) and PowerShell (`Get-TextSha256` on the misdecoded
  string). Em-dash in a JSONL row silently breaks `registry_row_sha256`.
- XAUUSD cost evidence set is symbol-level and reusable per-EA (copied to
  `EA_VwapFade/research/evidence/`); the commission $7/lot bound references
  governed-run lifecycles generically.
- Same 2 BLOCKED gates as AMA: `slippage_summary` WARN (tester produces no
  per-deal slippage samples — modeled, expected) and
  `invocation_artifact_freshness` (chart capture + late-created artifacts).
  Neither is strategy-material.
