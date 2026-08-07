# HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010 — frozen economic preregistration

Frozen after the HYP-009 engineering probe passed and before any full-window economic run.

## Fixed mechanism

Closed displacement BOS/MSS arms a structural event. A later closed retest/reclaim may enter only when the TB v3 causal pool exposes a confirmed, still-unconsumed swing-liquidity level ahead of price. The level must leave at least 1.25R actual runway after the frozen structural stop; target is capped at the smaller of fixed 1.5R and that real objective. AIRD/VRC are context vetoes; QQE is only a strongly opposed acceleration veto; MBB supplies location, not a future label.

HYP-009 verified 2,048 ready bars, zero snapshot failures, positive objective/runway coverage, exact sidecar reconciliation and no wrong-side objectives. No code or strategy parameter changes are permitted between that probe and this run.

## Frozen execution

- EA source SHA-256: `05D13CAF75B05D3B2585493734B3E315BFCB84004BFB989D228E08B0C79C257A`
- TB source SHA-256: `3848CBD4FD34748BE95A372D4797465383CC7EDDE0ED36687E8AA26546893539`
- EURUSD M5, 2018.01.01–2022.12.31
- Model 0, execution 0, current spread, 100000 USD, 1:100
- Exactly one development economic trial; no optimization, timezone, route, direction, year, validation or holdout pruning.

## Exact overrides

`InpAllowBreakoutMode=true;InpAllowRangeMode=false;InpAllowTrendMode=true;InpEnableTelemetry=true;InpExpectedSymbol=EURUSD;InpHypothesisId=HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010;InpMagic=5867420;InpManualModeMask=6;InpManualSessionMask=6;InpProfileMode=1;InpResearchAutoMode=true;InpStructuralExpiryBars=8;InpStructuralInvalidationAtr=0.20;InpStructuralMaxExtensionAtr=0.35;InpStructuralMinObjectiveR=1.25;InpStructuralQqeVetoThreshold=3.0;InpStructuralRequireLiveObjective=true;InpStructuralRetestToleranceAtr=0.15;InpStructuralUseLiquidityPoolObjective=true;InpUseContextRouter=true;InpUseQqeTiming=true;InpUseRoleAwareSequence=false;InpUseStructuralEventSequence=true;InpUseTbStructure=true;InpUseTemporalSequence=false;InpVariantTag=LIQUIDITY_POOL_ECONOMIC_V1`

## Decision gates

- Engineering invalid if any snapshot fail counter is nonzero, sidecar counts disagree, or objective geometry violates the logged invariants.
- Mechanism invalid if no-objective rejects are not below 5,598 or runway rejects are zero.
- Immediate economic kill if trades `<100`, PF `<=1.0`, mean achieved R `<=0`, or DD `>8%`.
- Robustness only if trades `>=100`, PF `>1.0`, mean achieved R `>0`, and DD `<=8%`.
- Promotion remains forbidden until cost stress, sensitivity, WFA/CPCV/DSR and Monte Carlo pass.
