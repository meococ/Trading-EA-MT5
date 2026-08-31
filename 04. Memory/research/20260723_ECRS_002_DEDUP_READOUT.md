# ECRS-002 De-dup / Failure-Radius Readout — HYP-ECRS-EURUSD-M5-002

Date: 2026-07-23 (UTC)
Author: parent agent (Owner approved "Option A" in-session, 2026-07-23)
Parent record: `HYP-ECRS-EURUSD-M5-001`
(`PARK_STAGE0_CADENCE_INFEASIBLE_NO_OUTCOME_READ`, 2026-07-22; readout
`03. EA Developer/EA_ECRS_CompressionReleaseScalper/research/HYP-ECRS-EURUSD-M5-001_STAGE0_READOUT.md`).
De-dup memo of 001: `04. Memory/research/20260722_ECRS_DEDUP_READOUT.md`
(adverse priors declared there carry over verbatim and are not repeated).

## 1. What changes vs 001 (the delta)

| Axis | 001 (parked) | 002 (this ID) |
|---|---|---|
| Entry gate set | ER shift + ATR compression + 12-bar breakout + **tick-volume surge >= 1.7x SMA20** + EMA20 bias + session/news/spread | ER shift + ATR compression + 12-bar breakout + EMA20 bias + session/news/spread — **volume surge REMOVED as a gate** (recorded as a per-candidate diagnostic feature only, never consulted by any rule) |
| Everything else | — | unchanged: same symbol/TF (EURUSD M5), same windows (verdict 2019-2022, sealed 2023+), same exit shell (SL 1.6xATR / TP 1.6R / 18-bar time stop), same session 07:00-16:30 UTC, same news/spread gates |

## 2. Why this is legal (not a rescue)

- 001 was parked at Stage-0 with **zero trade outcomes read** (outcome-blind
  attestation hash-bound in its funnel JSON). No PnL, win rate, or excursion
  from 001 exists anywhere to inform 002. A rescue requires an outcome to
  rescue from; there is none.
- **Declared use of 001 frequency data** (required by 001's park radius): the
  choice to remove the volume gate is informed ONLY by 001's frequency-plane
  funnel — the 1.7x surge gate removed 84% of in-session breakout candidates
  (462 -> 75) and concentrated survivors at 22:00-00:00 UTC where the trailing
  tick-volume baseline is thinnest. Mechanism rationale, independent of any
  outcome: retail tick volume is a broker-specific noise proxy (standing
  caveat, Sonic S677/S679), so a hard multiplicative gate on it is the least
  defensible component of the report object; ER regime-shift remains the
  direction/quality filter, which is the report's actual novel claim.
- 001's ID is never revived: 002 is a **different object** (different gate
  set = different decision surface) under a fresh ID with its own memo,
  registry row, and — if it reaches freeze — its own PROBE_PLAN.

## 3. Classification

`DEDUP_PASS_MATERIALLY_RESCOPED_PRE_OUTCOME` — new ID
`HYP-ECRS-EURUSD-M5-002`, same package `EA_ECRS_CompressionReleaseScalper`,
feature family `closed-bar-fx-m5-kaufman-er-regime-atr-compression-range-breakout-no-volume-gate`.

## 4. Pre-declared discipline for 002

- Stage-0 v2 stays outcome-blind (frequency only). Mainline object = volume
  gate fully dropped. One secondary frequency line may be counted for a
  weakened gate (1.2x) as freeze-decision input; **exactly one** variant gets
  frozen, the other becomes a forbidden rescue.
- Cadence gate before any freeze: pooled 2019-2022 eligible-entry rate
  >= 1.0/elapsed week, else 002 parks exactly like 001 (no outcome read).
  Honest note recorded pre-scan: the all-gates ceiling from 001's funnel
  (G1^G2^G3 = 462 = 2.21/week before bias/session cuts) means 002 will land
  in GOAL band (2-5/week) only if the session share of the un-volume-gated
  population is high; if measured cadence is 1.0-2.0/week the lane may
  proceed to probe but the acceptance-contract band (2-5/week) remains a
  known promotion risk, declared now.
- If frozen: probe arms = A (002 object) + B (A + ADX(14)>18 rising), plus
  matched-random and time-shift controls; trial universe 4; DSR floor 0.95;
  same kill-gate table as the approved plan. Adverse priors list of 001
  applies unchanged; S191 "compression predicts expansion, not direction" is
  now tested MORE directly since ER is the only direction-quality filter.
- Forbidden as rescue if 002 dies at any stage: reinstating/re-weakening the
  volume gate at another multiple, ER/ATR threshold retunes, session/hour
  vetoes, the `ER - ER[2] >= 0.08` delta-definition swap, management-stack
  additions, other symbols/windows.
