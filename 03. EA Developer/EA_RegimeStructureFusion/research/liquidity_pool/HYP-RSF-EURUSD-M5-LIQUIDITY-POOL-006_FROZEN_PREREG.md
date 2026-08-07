# HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-006 — frozen preregistration

Frozen before implementation and before any economic run.

## Parent failure and fresh mechanism

Parent `HYP-RSF-EURUSD-M5-LIVE-OBJECTIVE-005` is terminal: its single Model-0 run rejected 5,598 events for no objective and opened zero trades. The cause is a data-contract impossibility, not a numeric threshold: TB exports only the latest swing and marks that swing consumed on the BOS/MSS bar.

This hypothesis adds a bounded causal pool of confirmed swing-liquidity levels inside TB SMC. A level enters only when its pivot is confirmed using the existing left/right swing rule. A high is removed after a closed candle closes above it; a low is removed after a closed candle closes below it. TB exports the nearest still-unconsumed high above the current closed price and the nearest still-unconsumed low below it. The EA may use only that forward level as the structural objective.

This is a new indicator/EA data contract. It is not a relaxation or parameter rescue of HYP-005.

## Frozen identity

- EA: `EA_RegimeStructureFusion`
- Parent EA SHA-256: `C2ACC82167746612C9EEE1DD91C9FE7C2E0E56CA64799E1A80C690BB131B1831`
- Parent TB indicator SHA-256: `489B6E6B74C4FCA6624B510DC9FF38FDBBDA0584C007B8FFEE3D8339D1CB879E`
- Symbol/timeframe: `EURUSD M5`
- Window: `2018.01.01` through `2022.12.31`
- Tester: Model 0, execution mode 0, current spread, deposit 100000 USD, leverage 1:100
- One development trial only; no optimization, route pruning, session pruning, validation or holdout access.

## Frozen implementation contract

1. TB buffer contract becomes v3 and adds nearest unconsumed liquidity high/low plus validity flags.
2. Pool capacity is a fixed engineering bound, not an optimizable parameter.
3. All pool mutation and publication are closed-bar only; shift 0 remains event-free.
4. The consumed BOS/MSS break level is never eligible as a forward target.
5. EA input `InpStructuralUseLiquidityPoolObjective=true` selects the new fields. Missing/wrong-side objective fails closed.
6. Existing minimum actual runway remains frozen at `1.25R`; target remains the smaller of fixed 1.5R and the real objective.
7. EntryContext must record pool objective and exact arm/entry geometry for every accepted order.

## Exact overrides

`InpAllowBreakoutMode=true;InpAllowRangeMode=false;InpAllowTrendMode=true;InpEnableTelemetry=true;InpExpectedSymbol=EURUSD;InpHypothesisId=HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-006;InpMagic=5867386;InpManualModeMask=6;InpManualSessionMask=6;InpProfileMode=1;InpResearchAutoMode=true;InpStructuralExpiryBars=8;InpStructuralInvalidationAtr=0.20;InpStructuralMaxExtensionAtr=0.35;InpStructuralMinObjectiveR=1.25;InpStructuralQqeVetoThreshold=3.0;InpStructuralRequireLiveObjective=true;InpStructuralRetestToleranceAtr=0.15;InpStructuralUseLiquidityPoolObjective=true;InpUseContextRouter=true;InpUseQqeTiming=true;InpUseRoleAwareSequence=false;InpUseStructuralEventSequence=true;InpUseTbStructure=true;InpUseTemporalSequence=false;InpVariantTag=LIQUIDITY_POOL_CAUSAL_V1`

## Pre-run gates

- Indicator and EA compile with zero errors.
- Targeted pool lifecycle, closed-bar and no-lookahead tests pass.
- Non-repaint audit passes.
- Registry row, task packet, EX5, indicator dependencies, parameters and receipt are SHA-bound.
- Required sidecars: LifecycleTrades, EntryContext, RunMeta.

## Decision gates

- Engineering invalid if pool fields are missing, shift-0 dependent, or EntryContext/Lifecycle counts disagree.
- Mechanism invalid if no-objective rejects do not fall materially below the parent's 5,598 or if runway rejects remain zero.
- Immediate economic kill if trades `< 100`, PF `<= 1.0`, mean achieved R `<= 0`, or drawdown `> 8%`.
- Robustness is authorized only if trades `>= 100`, PF `> 1.0`, mean achieved R `> 0`, and drawdown `<= 8%`.
- Promotion remains forbidden until cost stress, sensitivity, WFA/CPCV/DSR and Monte Carlo all pass.

No same-ID parameter, timezone, route, direction or year rescue is allowed.
