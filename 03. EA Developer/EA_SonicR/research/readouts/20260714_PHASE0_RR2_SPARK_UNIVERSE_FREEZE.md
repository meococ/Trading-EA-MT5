# Phase-0 universe freeze — RR2 + Spark100k (a priori)

Date: 2026-07-14 ~22:50 ICT  
Status: `UNIVERSE_FROZEN_A_PRIORI / COMPOSE_CEREMONY_NOT_RUN`  
Authority: Owner Wave5 optional item — freeze exact list **before** combo metrics  
GPT: waived

## Frozen exact universe (no PF/outcome selection)

| Sleeve | hypothesis_id | Authoritative run_id | Role |
|---|---|---|---|
| SB RR2 friction | `HYP-SB-MAXKZ2-RR2-FRICTION-001` | `20260714_194548` | Sleeve A (twin `194221` same metrics — **not** selected as "best") |
| Spark Asian capacity 100k | `HYP-SPARK-CAPACITY-3PD-001` (Spark100k shelf) | `20260714_193358` | Sleeve B |

## Frozen compose contract (metadata only)

| Field | Frozen |
|---|---|
| Join | Equal 1:1 trade-series union on common calendar window |
| Window | Intersection of both run windows (no cherry year) |
| Weights | Equal risk weight; no PF-weighted blend |
| Cost stress | A priori only; same haircut applied to both sleeves |
| Contamination | Prior offline compose JSON / Real-P50 equal-join = **diagnostic only**; **not** this freeze’s metrics |
| Blockers still open | Phase-0 contamination clearance; Spark module gaps on portfolio scaffold path; `COST_PROVENANCE_GAP` NARROWED_NOT_CLEARED |

## Explicit non-claims

- This document does **not** authorize GOAL / confirmed / portfolio-sleeve.
- This document does **not** re-read or re-rank prior combo PF as ceremony.
- No new combo PF/tpw is published in Wave5 from this freeze.
- Next compose ceremony requires independent review after contamination contracts clear.

## Why freeze now

Wave4 lesson: do not glue thick-sparse + cadence sleeves post-hoc. RR2+Spark
is the only near-joint Demo shelf; freezing exact run IDs a priori prevents
outcome-selected universe drift before any future compose metrics.
