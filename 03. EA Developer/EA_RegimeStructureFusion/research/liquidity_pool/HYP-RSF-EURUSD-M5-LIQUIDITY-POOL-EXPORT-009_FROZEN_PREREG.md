# HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-EXPORT-009 — frozen preregistration

Frozen before the TB public-buffer export correction.

## Mechanism and engineering correction

The strategy mechanism remains the HYP-006 causal pool of confirmed, unconsumed swing-liquidity levels. Probe HYP-008 isolated the blocker: TB buffer 46 failed on all 2,112 eligible bars because buffers 44–47 were outside `indicator_plots`.

Only the indicator export surface changes:

- `indicator_plots` becomes 48.
- plots 44–47 are `DRAW_NONE`, visible to `CopyBuffer` but not chart-cluttering.
- buffers 44/45 remain nearest forward liquidity prices; 46/47 remain their availability flags.
- calculation buffer 48 and all strategy parameters/rules remain unchanged.

## Staged authorization

1. Compile/tests/non-repaint audit.
2. One January-2018 Model-1 engineering probe. It has no economic authority and must produce `indicator_ready>0`, zero TB46 read failures, and a coherent snapshot funnel.
3. Only after step 2 passes, append a screened registry state and run exactly one EURUSD M5 2018–2022 Model-0 economic trial.

## Economic contract

- Same exact strategy overrides as HYP-007 except ID `HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-EXPORT-009`, magic `5867419`, variant `LIQUIDITY_POOL_EXPORTED_V1`.
- Current spread, execution 0, deposit 100000 USD, leverage 1:100.
- Immediate kill if trades `<100`, PF `<=1.0`, mean achieved R `<=0`, or DD `>8%`.
- Mechanism invalid if no-objective rejects do not fall below 5,598 or runway rejects remain zero.
- No parameter, timezone, route, direction or year rescue. Robustness only after all raw gates pass.
