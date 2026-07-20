# HYP-ICT-FVG-FIDNEWS-EURUSD-M5-002 — frozen Model-0 plan

Status: **FROZEN BEFORE ANY MODEL-0 OUTCOME READ**

## Identity and lineage

- Parent terminal record: `HYP-ICT-FVG-FID-EURUSD-M5-001` (`parked`, no
  Model-0 outcome read).
- Reason for a new ID: the canonical registry forbids transitions out of
  `parked`. This child adds the previously unavailable hash-bound news input;
  it is not a result-driven rescue.
- EA: `EA_ICTFVGReportFidelity`, EURUSD M5 with closed M15 structure/ADX.
- Report SHA-256:
  `44638AA4999D35AF3C4B3CCA3C1D530D2AC1CCF6901D73A4291D2649687F4070`.
- Development/evaluation window: 2019-01-01 through 2022-12-31.
- 2023 onward remains sealed and must not be loaded.

## Frozen arms and rules

Exactly two Model-0 arms are allowed:

1. `SIGNAL_HIGH_RECALL_CONTROL`: sweep/reclaim control.
2. `SIGNAL_REPORT_FIDELITY`: ordered sweep -> displacement+strict FVG -> fresh
   OB/FVG overlap -> closed-M15 MSS -> first 50-70% retest/rejection ->
   closed-M15 ADX >25.

All signal, risk, execution, session, SL/TP, cooldown, daily-loss, drawdown,
breakeven and flattening parameters remain exactly as frozen in the parent
plan. No optimization or result-driven threshold change is authorized.

Frozen delta:

`InpRequireNewsGuard=true;InpNewsBlackoutMinutes=30`

## News evidence

- Source-C Forex Factory weekly pages, 209 consecutive weeks from
  `dec30.2018` through `dec25.2022`.
- 1,282 timed EUR/USD high-impact events, unique event IDs, GMT+7 converted to
  UTC, local event dates restricted to 2019-2022.
- Raw SHA-256:
  `78CB2656A27278B1DA04B2C594A2C73BB1877DBA3AB52BCCFAC36A215945EA8F`.
- CSV SHA-256:
  `80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307`.
- Generated include SHA-256:
  `248D569B981564AC0B179588C4919CD6CC196A9E7B008939A9CCDB3446F4678C`.
- Validator anchors: 48 exact NFP rows, 33 FOMC statements, 23 ECB main
  refinancing decisions, and the Dec-2022 CPI/FOMC/ECB cluster present.
- Untimed EUR/USD (24) and global events (63) are audit-only and not assigned
  fictional timestamps.

The calendar is diagnostic source C. It does not confer promotion eligibility.

## Costs and verdict boundary

- Fixed diagnostic stress: 1.5, 2.25 and 3.0 pip round trip.
- Same-broker spread export failed provenance because 24.5552909% of 1,491,312
  M1 rows report zero spread. Commission and direction-aware slippage remain
  unverified.
- Every run has `promotion_eligible=false`.
- Model 0 may decide engineering viability, cadence and diagnostic economics.
  It cannot pass the final cost gate or authorize live/paper use.
- If the challenger misses 2.0-5.0 trades per elapsed week, 300 closed trades,
  PF 1.6 at base diagnostic cost, stress PF gates, or 8% max-DD gate, kill it.
- A positive diagnostic result is `INCONCLUSIVE_COST_UNVERIFIED`, not a
  promotion or claim of superiority.

## Frozen implementation binding

The source hash will be registered after changing only the embedded hypothesis
identity from the terminal parent to this child, followed by a clean
AlphaFactory compile and a new source->include->EX5 receipt. No tester outcome
has been opened at this freeze point.
