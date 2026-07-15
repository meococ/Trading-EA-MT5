# Deliverable — Wave7-continue QFSI / Real shelf reprice

Date: 2026-07-14 ~23:50 ICT  
Authority: Owner CONTINUE after `WAVE7_EXECUTED_EMPTY`  
GPT: waived · Grok · no-Git · cost honesty absolute

## Verdict

**`REAL_ON__QFSI_005_LIVE__PARTIAL_SHELF_REPRICE_COMPLETE`.**  
Full QFSI still **`STOP_DATA_FRONTIER`**. GOAL unmet. Demo PF is not confirmed.

Receipt content SHA `CE6DC459EE55F2E68BBB25DB737D31A0809CDDA07A37CE42FB1454FBCB76842B`

## 1) Live Real / QFSI status (do not kill)

| Item | Value |
|---|---|
| Probe V8 | `TARGET_SERVER_READONLY_PROBE_COMPLETE` · server_match=true |
| Live login | **26451822** @ `FivePercentOnline-Real` · balance $99971.68 · trade_allowed=True |
| Processes | terminal64 **29076** + QFSI python **35892** (005) — **left running** |
| Capture | `20260714_QFSI_REAL_005_POSTAUTH` LIVE (~1h window; ETA ~00:23 ICT) |
| Quote days | **1** (need 90) |
| Commission unique EURUSD | **2** (need ≥30/symbol) |
| Slippage fills | **0** (MISSING ≠ 0) |

## 2) Cost model (partial — not confirmed)

- Unit USDJPY P50 **$5.2335/lot** = capture-spread P50 + EURUSD commission clue **$4.00/lot RT** (unique N=2)
- Canonical lot-0.5 trade P50 **$2.6168** (matches prior hygiene table)
- Slippage: **MISSING ≠ 0** (not invented)
- Table: `preflight/20260714_BROKER_SPREAD_COST_TABLE_QFSI_W7CONT.json` SHA `13B7306FE3AA4D187124C953A582676F4DCABDA3204961B260A7996E88302440`

## 3) Shelf reprice (lot-scaled)

| Book | run | base PF | x1 | x1.5 | x2 | GOAL stress |
|---|---|---:|---:|---:|---:|---|
| RR2 shelf | `20260714_194548` | 1.378 | 1.316 | 1.286 | 1.257 | **PASS** |
| RR2 fresh M0 | `20260714_231750` | 1.156 | 1.105 | 1.081 | 1.057 | **FAIL** |
| SB A1 | `20260714_002505` | 1.344 | 1.276 | 1.244 | 1.212 | **FAIL** |
| Spark 100k | `20260714_193358` | 1.380 | 1.302 | 1.264 | 1.228 | **PASS** |
| MaxKZ2 | `20260714_192304` | 1.334 | 1.267 | 1.235 | 1.204 | **FAIL** |
| RR2 194221 ctrl | `20260714_194221` | 1.378 | 1.316 | 1.286 | 1.257 | **PASS** |

Label: **`PARTIAL_REAL_COST`** — not full QFSI. PASS ≠ confirmed.

## 4) A1 + Spark compose (diagnostic)

pooled x1/x1.5/x2 PF **1.290 / 1.254 / 1.220** · tpw **3.24** · same-day overlap **108** · goal-like **False**

## 5) Friction vs GOAL

- Best shelf RR2 `194548` partial Real: x1/x1.5/x2 **1.316 / 1.286 / 1.257** → stress band PASS (partial only)
- Fresh Model0 `231750`: x1 **1.105** → PARK_MISS under present build
- A1 + MaxKZ2: FAIL x1.5 / x1 band
- Spark100k: stress PASS (partial) — still not confirmed
- Compose A1+Spark: goal-like False (x1 1.290)
- **Friction dead-end on Real: NOT confirmed** (quote-days/commission/slip gates open)
- Confirmed claim: **false**. Demo PF ≠ confirmed.

## 6) Next auto

1. Keep Real; let `005` finish; auto-launch `006` longer accumulate (4h) without killing Real.
2. No price-twin spam / no densify Wave6–7 / no blind COT revive.
3. When QFSI gates lift → re-bind RR2 family under full cost grade.
4. Owner optional: deal-export drop for commission/slip (no invented fills).
