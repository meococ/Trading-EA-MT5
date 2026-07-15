# HYP-PORTFOLIO-COMPOSE-001 — Phase 0 Candidate Subset Identity Readout

Date: 2026-07-13
Status: `DRAFT_SUBSET_NOT_FROZEN` / `PHASE1_BLOCKED` / **GOAL unmet**

## Decision

Price-M15 dual-filter shelf is EMPTY (kill/park list exhausted).
Shortest legal autonomous path without Real login: Phase 0 portfolio
identity subset freeze work for `HYP-PORTFOLIO-COMPOSE-001`.

## Selection rule (non-outcome)

- Fixed hypothesis IDs: `HYP-SB-WEEKEND-FLAT-001`, `HYP-SPARK-ASIAN-M15-001`
- Run bind from latest registry `run_ids` (challenger = last of two)
- No PF / net / cadence ranking

- `subset_universe_sha256`: `36D7AA47A191A72A493F6752C698C5D508B46F636404442BD1A3E13B2E678C4F`
- Artifact: `03. EA Developer/EA_SonicR/research/preflight/20260714_PHASE0_PORTFOLIO_CANDIDATE_SUBSET_IDENTITY_V1.json`

## Members (identity only)

| hypothesis_id | member | structural | key blockers |
|---|---|---|---|
| `HYP-SB-WEEKEND-FLAT-001` | `EA_SilverBullet/20260714_002505` | eligible_identity_only | MISSING_TRADE_SERIES_PATH, MISSING_COST_ARTIFACT, COST_PROVENANCE_UNVERIFIED_TESTER_OR_MISSING |
| `HYP-SPARK-ASIAN-M15-001` | `EA_M15SparkAsian/20260714_002614` | eligible_identity_only | MISSING_TRADE_SERIES_PATH, MISSING_EQUITY_SERIES_PATH, MISSING_COST_ARTIFACT, COST_PROVENANCE_UNVERIFIED_TESTER_OR_MISSING |

## Phase 0 verdict

**`BLOCKED_NOT_READY_FOR_PREREG_FREEZE`**

Contamination attestation still requires a clean future freeze review.
Cost provenance remains unverified (Demo tester / missing).
No Phase 1 composition, compile, or backtest authorized by this readout.

## vs GOAL

No research-pass and no confirmed book. Cadence/PF of a composed book
were **not** computed (outcome access forbidden in Phase 0).

## Next

1. Owner freeze review of this exact subset + weight/common-window contracts.
2. FivePercentOnline-Real login + QFSI cost capture.
3. New independent M15/exogenous thesis outside kill shelf (self-research).
