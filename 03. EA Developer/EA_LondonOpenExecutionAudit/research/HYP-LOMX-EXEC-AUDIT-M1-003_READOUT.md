# HYP-LOMX-EXEC-AUDIT-M1-003 — Audit-only MQL5 successor readout

## Verdict

`PASS_ENGINEERING_EXECUTION_FIDELITY_ONLY__PARK__PARENT_HYP002_KILL_UNCHANGED`

The successor followed all four frozen trade scenarios on FivePercent Model 0 over TRAIN 2016-2020. Decision telemetry, lifecycle-v3 rows, RunMeta, and MT5 report deals reconcile for 5,171 completed lifecycles. This is not an economic survivor: performance, validation, holdout, optimization, promotion, paper and live authority remain false. The terminal economic verdict of `HYP-LOMX-MULTI-M1-002` is unchanged.

## Engineering build

- Canonical source: `EA_LondonOpenExecutionAudit.mq5`
- Source SHA256: `C99D18C7912384D529CF651214EBF636211536957D7F4241831CB2418D28EEC1`
- Final EX5 SHA256: `3CF2F5B988D594F3B2EDCBEDECB45957F1984C30E2B6AD5D70D29F2812E8D148`
- MetaEditor: `0 errors, 0 warnings`
- Focused tests: `11 passed`
- Non-repaint: exact `iBarShift(..., true)` plus `CopyRates(..., shift, 1, ...)`; `shift >= 1`; no bar-zero indicator/source read.
- Independent Grok forensic review: PASS after pre-outcome fixes for time-gate, zero-population, report-reconciliation and deal-history telemetry gaps. Total Grok cost: USD `0.3620888`.

## Model-0 audit matrix

All runs used M1 real ticks, 2016.01.01-2020.12.31, fixed 0.01 lot, one owned position maximum, no SL/TP and no optimization. History quality is 100% in every report.

| Scenario | Run | Signal / entry / exit London | Completed | Report PF* | Net* | Spread p50 / p95 |
|---|---:|---|---:|---:|---:|---:|
| EURUSD MIDDAY continuation | `20260730_190022` | 08:31 / 08:31 / 12:00 | 1,292 | 0.866335 | -148.86 | 0.7 / 0.8 pip |
| GBPUSD MIDDAY reversal | `20260730_190128` | 08:31 / 08:31 / 12:00 | 1,293 | 0.931270 | -129.34 | 1.1 / 1.5 pip |
| GBPUSD LATE_FIX reversal | `20260730_190227` | 08:31 / 15:30 / 16:00 | 1,293 | 0.877301 | -121.24 | 1.1 / 1.3 pip |
| GBPUSD FULL_SESSION reversal | `20260730_190328` | 08:31 / 08:31 / 16:30 | 1,293 | 0.913842 | -265.66 | 1.1 / 1.5 pip |

`*` MT5 report economics are retained as diagnostic observations only. The hypothesis never authorized performance inference, cost validation or economic promotion.

EURUSD generated 1,858,630 bars / 118,088,456 ticks. Each GBPUSD run generated 1,858,445 bars / 134,979,093 ticks. Request-to-deal delta was exactly 0.0 pip at entry and exit in this tester contract; this is tester execution, not independent live slippage evidence.

## Scenario-following proof

The fail-closed validator found, for every scenario:

- 100% of signal observations at London 08:31, after the 08:30 M1 bar closed;
- 100% of entries inside the frozen gate and 100% of exits not before the frozen exit gate;
- continuation polarity only for EURUSD MIDDAY and reversal polarity for the three GBPUSD cells;
- BUY entry requests at Ask and SELL entry requests at Bid; exit requests on the opposite executable side;
- exact equality of `signals = entry deals = lifecycle opens = exit deals = final lifecycle closes = MT5 report entries/exits` within each cell;
- no overlapping owned position and zero overnight violations.

Representative 2018-07-02 records:

| Scenario | 08:00 open -> 08:30 open | Formation / polarity -> direction | Entry request = deal | Exit request = deal |
|---|---|---|---|---|
| EUR MIDDAY_CONT | 1.16525 -> 1.16337 | -1 / +1 -> SELL | 08:31, 1.16337, deal 1294 | 12:00, 1.16422, deal 1295 |
| GBP MIDDAY_REV | 1.31804 -> 1.31662 | -1 / -1 -> BUY | 08:31, 1.31659, deal 1294 | 12:00, 1.31637, deal 1295 |
| GBP LATE_FIX_REV | 1.31804 -> 1.31662 | -1 / -1 -> BUY | 15:30, 1.31045, deal 1294 | 16:00, 1.31230, deal 1295 |
| GBP FULL_SESSION_REV | 1.31804 -> 1.31662 | -1 / -1 -> BUY | 08:31, 1.31659, deal 1294 | 16:30, 1.31238, deal 1295 |

## Invalid pre-run correction

Attempt `20260730_185647` is engineering-invalid, not an economic observation. The host account has an absolute stop-out threshold of USD 91,401.46, which exceeded the initial USD 10,000 diagnostic deposit and forced the first EURUSD position closed after one minute. Before any valid full-horizon outcome, V2 task packets raised diagnostic deposit to USD 500,000 only. Signal logic, scenario mapping, 0.01 lot, dates, Model 0 and all audit gates remained unchanged. The invalid attempt is hash-bound in every V2 receipt.

## Authoritative evidence

- `research/evidence/HYP-LOMX-EXEC-AUDIT-M1-003_MODEL0_AUDIT_READOUT.json` — validator PASS, SHA256 `7F7A6D248164D2A216E33DB6A3874B820BB9A5C9486051B5CC539664B8FF86FA`
- `research/evidence/HYP-LOMX-EXEC-AUDIT-M1-003_EXECUTION_DASHBOARD.json` — audit summary, SHA256 `C3571435A171D104BB2466D259DFA3A0295A63300081D408342045E3FE88D002`
- `research/evidence/HYP-LOMX-EXEC-AUDIT-M1-003_EXECUTION_DASHBOARD.png` — visual control, SHA256 `59BD3051EBEB5A232AC2353CCCAF3CDCF3154ADEA1E9F4F4F4F228BD6D1D3EB8`
- Run manifests: `FA877987...26A`, `085D1F14...52C9`, `AA85AA29...FB78`, `93EE7597...EEF`.

## Decision

Park this audit successor. It proves that the MQL5 implementation can execute the frozen narrative faithfully at scale; it does not create edge. All four diagnostic PF values are below 1, which is directionally consistent with the killed parent, but no new economic claim is made and sealed later years remain unopened.
