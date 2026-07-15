# De-dup clearance — Discovery Wave7

Date: 2026-07-14  
Authority: Owner CONTINUE Wave7 after `WAVE6_EXECUTED_EMPTY` / HARD_EMPTY  
GPT: waived · Grok · free MT · no-Git  
Status: `A_PRIORI_CLEARANCE_BEFORE_PROBE`

## Forbidden densify (hard)

Wave6 mother / 3-day lookback-body-RR / USDCHF London / FX3 bodyATR·3-day
pools · V1–V8 full board · MaxKZ/RR2/SB-Spark · USBILL · IB/GBPJPY/ATR%ile ·
PIN/Outside/Engulf · EURGBP-lead · AUDUSD overlap-fail · JPY-cross catch-up ·
London-open-drive / NY-open-drive hour retune · PWHL sweep · Weekly-HL H4 ·
RV-compress ratio retune · Asia/London/NY IB hour mine from Wave4–5 readouts.

## Inventory — unused price-lawful objects (Wave7 picks)

| Object class | Prior collision | Wave7 ID |
|---|---|---|
| NZDUSD Asia→London range break | EURUSD Asia-box Wave5 PARK/KILL path; USDCHF London KILL (diff symbol+box) | W7-1 |
| Prior **week open** accept/cont | Weekly-HL H4 KILL; PWHL sweep-reclaim KILL (HL wick ≠ week open) | W7-2 |
| London **session mid** reclaim cont | Asia mid fail-fade V4/V5; VWAP reclaim KILL | W7-3 |
| AUDUSD impulse lead → EURUSD | GBPJPY→USDJPY PARK; EURGBP→EURUSD KILL; AUDJPY→USDJPY KILL | W7-4 |
| Weekend gap fill (Mon H1) | USDJPY D1 gap fade STARVE; no day-of-week mine | W7-5 |
| Compose thick parks 3-day + London-open-drive | FX3 same-rule pool KILL; SB+Spark compose pattern OK if a priori + overlap+stress | W7-6 |

## Independence contracts

### W7-1 — `HYP-NZDUSD-H1-ASIA-RANGE-LONDON-BREAK-001`

Asia [0,7) H1 box lock → London [7,16) closed-bar break + 1-bar accept outside
box → cont RR=3; MaxPerDay=1. Symbol **NZDUSD** only.

### W7-2 — `HYP-W1-OPEN-H1-ACCEPT-CONT-001`

Prior complete week’s **open** (not H/L) as level; H1 close beyond WO by
≥0.15 ATR + body≥0.45 ATR → cont RR=3; MaxPerWeek=1. USDJPY.

### W7-3 — `HYP-H1-LONDON-MID-RECLAIM-CONT-001`

London [7,12) range mid; pierce beyond mid then closed reclaim back through
mid in direction of pierce → cont RR=3; MaxPerDay=1. USDJPY. Not fade-to-mid.

### W7-4 — `HYP-AUDUSD-LEAD-EURUSD-H1-001`

Closed AUDUSD H1 body≥0.70 ATR impulse → EURUSD same-dir closed bar within
lag∈{1,2} with body≥0.40 ATR → cont RR=2.5. Not GBPJPY/EURGBP/AUDJPY clones.

### W7-5 — `HYP-EURUSD-H1-WEEKEND-GAP-FILL-001`

Friday last H1 close vs Monday first tradeable H1 open gap ≥0.35 ATR → fade
toward Friday close; SL beyond Monday extreme; RR=2.0 to fill or partial;
MaxHold=12 H1. No Mon/Tue/… filter beyond weekend gap definition.

### W7-6 — `HYP-BOOK-COMPOSE-3DAY-LONDONDRIVE-001`

A priori equal-join of frozen offline sleeves:
- `HYP-H1-THREE-DAY-HIGHLOW-BREAK-001` (Wave6B PARK; do not retune)
- `HYP-H1-LONDON-OPEN-DRIVE-001` (EQHL Wave4 thick cadence-kill; do not densify)

Measure pooled PF / tpw / +$12 x1.5·x2 + same-day entry overlap. **Not**
Phase-0 SB/Spark reopen. Survive only if joint screen near/pass.

## Gates

Joint screen: PF>1.30 ∧ tpw∈[2,5] ∧ x1.5≥1.25 ∧ x2≥1.00.  
Model 0 only if `PROBE_SURVIVOR`. Cost: `UNVERIFIED_OFFLINE_PROXY`.
