# Design memo — W22 architecture monetization

## Problem

Local OHLC HARD PIVOT W1–W21 saturated ALL_KILL. Best near-miss W14
H4-retest PF@$12=1.221 — densify forbidden. Thick edges miss cadence;
dense edges die under +$12. Need architecture that changes **inventory**
or **book concurrency**, not another OHLC entry template.

## Design A — Same-day flat (no overnight inventory)

GOAL scalp contract limits overnight exposure. On frozen RR2, keep only
trades that close same calendar day. Tests whether overnight legs are
friction sinks. ≠ `HYP-SB-WEEKEND-FLAT-001` (Fri-only).

## Design B — Sequential single-open slot

Clean heat-pool only collapses same (symbol, M15-bar). Concurrent
overlap across sleeves still compounds friction + correlation.
Hard seq-slot: refuse new open while any book trade is open.

## Abandoned pre-freeze

Costfloor risk_usd>=2×$12 is vacuous on 0.5-lot RR2 (all risk≳$38).
Not probed as a claim; replaced by same-day flat.

## Deep Research

Browser ChatGPT session on login wall — packet not submitted.
Continue Track 2 without waiting.
