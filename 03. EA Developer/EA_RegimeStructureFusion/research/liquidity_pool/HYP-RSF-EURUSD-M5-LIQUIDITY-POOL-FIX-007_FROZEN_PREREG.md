# HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-FIX-007 — frozen preregistration

Frozen before the data-contract correction and before any economic run.

## Scope boundary

Parent HYP-006 is engineering-invalid, not economically evaluated: all 125,589 candidate decision bars failed snapshot readiness because unavailable liquidity price buffers returned `EMPTY_VALUE`. This hypothesis changes only the read contract:

- TB v3 validity flags 46/47 remain mandatory closed-bar reads.
- Liquidity prices 44/45 become optional reads with a zero fallback.
- A price is used only when its matching live flag is true and it is strictly ahead of the structure level.

No strategy parameter, session, route, direction, risk, stop, target, threshold or market-data window changes.

## Frozen execution

- EURUSD M5, 2018.01.01–2022.12.31
- Model 0, execution mode 0, current spread, 100000 USD, 1:100
- Exactly one economically valid development trial after engineering gates pass
- Overrides are identical to HYP-006 except ID `HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-FIX-007`, magic `5867397`, and variant `LIQUIDITY_POOL_OPTIONAL_READ_FIX_V1`.

## Frozen gates

- Engineering: indicator_ready must be greater than zero; required sidecars present; EntryContext rows equal accepted entries; closed-bar/no-lookahead tests and compile pass.
- Mechanism: no-objective rejects must be lower than HYP-005's 5,598 and runway rejects must be greater than zero.
- Immediate kill: trades `<100`, PF `<=1.0`, mean achieved R `<=0`, or DD `>8%`.
- Robustness only if trades `>=100`, PF `>1.0`, mean achieved R `>0`, DD `<=8%`.
- No same-ID parameter/timezone/route/year rescue. Promotion remains forbidden until cost stress, sensitivity, WFA/CPCV/DSR and Monte Carlo pass.

## Exact overrides

`InpAllowBreakoutMode=true;InpAllowRangeMode=false;InpAllowTrendMode=true;InpEnableTelemetry=true;InpExpectedSymbol=EURUSD;InpHypothesisId=HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-FIX-007;InpMagic=5867397;InpManualModeMask=6;InpManualSessionMask=6;InpProfileMode=1;InpResearchAutoMode=true;InpStructuralExpiryBars=8;InpStructuralInvalidationAtr=0.20;InpStructuralMaxExtensionAtr=0.35;InpStructuralMinObjectiveR=1.25;InpStructuralQqeVetoThreshold=3.0;InpStructuralRequireLiveObjective=true;InpStructuralRetestToleranceAtr=0.15;InpStructuralUseLiquidityPoolObjective=true;InpUseContextRouter=true;InpUseQqeTiming=true;InpUseRoleAwareSequence=false;InpUseStructuralEventSequence=true;InpUseTbStructure=true;InpUseTemporalSequence=false;InpVariantTag=LIQUIDITY_POOL_OPTIONAL_READ_FIX_V1`
