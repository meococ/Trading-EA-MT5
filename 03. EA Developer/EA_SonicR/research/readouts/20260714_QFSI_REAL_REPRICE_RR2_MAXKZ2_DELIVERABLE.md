# Deliverable — QFSI Real unblock + RR2/MaxKZ2 reprice

Date: 2026-07-14 ~20:51 ICT  
Process: no GPT; canonical `execution_data_qfsi_nolive_capture.py` + probe V4  
Language: tiếng Việt (Owner) / evidence EN

## 1) MT5 server

| Field | Value |
|---|---|
| Expected | `FivePercentOnline-Real` |
| Observed | `FivePercentOnline-Real` |
| Probe | `TARGET_SERVER_READONLY_PROBE_COMPLETE` |
| Probe file | `preflight/v4_data/20260714_MT5_READONLY_PROBE_V4.json` |
| Probe SHA256 | `7C38E9DC2166FBAF269ABFB3E34AF30032EE04A3FC0A7CEF7BD1F3FCF3CDF6A3` |

## 2) QFSI capture evidence

| Field | Value |
|---|---|
| Capture ID | `20260714_QFSI_REAL_002` |
| Status | `CAPTURE_WINDOW_COMPLETE_PARTIAL` |
| Manifest SHA256 | `37033C3862BA145A3B1D7091D5BD61A4A80C47F90FA2BA0AC946BFE61EFB6CED` |
| Quotes / heartbeats | 421 / 440 |
| Commission lifecycles | EURUSD=2, GBPUSD=0, XAUUSD=0, USDJPY=0 |
| Slippage fills | 0 (MISSING, not zero) |
| `reprice_ready` (full QFSI) | **false** |
| Blockers | QFSI_SAMPLE_GATES_NOT_MET; SLIPPAGE_FILLS_MISSING; COMMISSION_SAMPLE_BELOW_30; QUOTE_ELAPSED_DAYS_BELOW_90 |

Path: `02. AlphaFactory/evidence/execution/FivePercentOnline-Real/20260714_QFSI_REAL_002/`

**Honesty:** full QFSI gate vẫn FAIL. Đây là Real live-spread + EURUSD commission clue (N=2), không phải confirmed cost provenance.

## 3) Cost model (USDJPY)

| Input | Value |
|---|---|
| Lot P50 (RR2 report) | 0.5000 |
| Spread USD/lot P50 | 0.617505 |
| Spread USD/lot P90 | 1.235010 |
| Commission clue RT/lot | $4.00 (EURUSD N=2 transferred) |
| Base $/trade P50 | **2.3088** |
| Base $/trade P90 | **2.6175** |
| Prior Demo proxy | $12.00/trade |

## 4) Reprice / stress vs GOAL gates

GOAL: PF>1.30 @x1; x1.5 PF≥1.25; x2 PF≥1.00 (after verified cost). Cadence already near-GOAL on tester books.

| Book | Scenario | x1 PF | x1.5 PF | x2 PF | GOAL cost-stress |
|---|---|---:|---:|---:|---|
| RR2 `194221` | Real P50 | 1.323 | 1.297 | 1.271 | PASS |
| RR2 `194221` | Real P90 | 1.316 | 1.286 | 1.257 | PASS |
| MaxKZ2 `192304` | Real P50 | 1.275 | 1.246 | 1.218 | FAIL |
| MaxKZ2 `192304` | Real P90 | 1.267 | 1.235 | 1.204 | FAIL |

Decision: `MIXED_PARTIAL_REAL_COST_ONE_SURVIVOR_PATH_FULL_QFSI_STILL_OPEN`

## 5) Next moves

1. Do **not** densify MaxKZ/RR.
2. If FAIL under Real partial cost: keep PARK; open next legal stub `HYP-H4-OUTSIDE-REV-001` (prereg before code) or other independent rebuild.
3. Full QFSI still needs ≥90d quotes + ≥30 commission/symbol + ≥100 slippage fills — Owner can accumulate over time; short capture cannot clear it.
4. No Spark compose promote while cost stress FAIL / QFSI partial.

## 6) hot.md?

Updated this turn: clear login blocker; record Real capture + partial reprice; COST_PROVENANCE_GAP = NARROWED_NOT_CLEARED.

## Receipt

`preflight/20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_RECEIPT.json`  
SHA256: `BE16E1C90B5FFFB467956C7ACFD8AA262558B4D0D23B01AA02C598E3A7B36F4E`
