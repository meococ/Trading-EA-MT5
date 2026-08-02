# EA_VRAS_RegimeAdaptiveScalperV4

The invalid three-engine EURUSD plan remains closed under
`HYP-VRAS-EURUSD-M5-015`. Its headline Hurst/VR/OU values came from the USDJPY
tail of a combined three-symbol DESIGN file, and its true-flow/estimator/async
contracts were not build-ready.

The package now contains the fresh, target-symbol-aligned successor
`HYP-VRAS-USDJPY-M5-001`:

- USDJPY M5, `[22:15,05:30) UTC`;
- one atomic closed-bar OU mean-reversion engine;
- synchronous tester-only order execution with server SL/TP;
- persistent daily/account risk latches and lifecycle-v3 telemetry;
- no CVD, VPIN, OFI, Volman, sweep, or multi-engine claim.

Current verdict:

`PARK_PRE_MODEL0_MISSING_USDJPY_COMMISSION_AND_SLIPPAGE_PROVENANCE`

Evidence status:

- P0: all 6 target-symbol structural gates passed on 1,286 DESIGN sessions;
- tests: 33 passed;
- compile: 0 errors, 0 warnings;
- canonical non-repaint audit: PASS, 0 findings;
- MT5/economic trials: 0;
- promotion/paper/live: false.

The FiveAssetFoundation parquet supplies historical USDJPY spread, but the
workspace has no hash-bound same-symbol commission or qualifying independent
slippage evidence. The frozen commission/slippage inputs are engineering stress
assumptions only. Model 0 remains fail-closed until that evidence gap is closed.

Start with:

- `research/HYP-VRAS-USDJPY-M5-001_PLAN_REVIEW.md`
- `research/HYP-VRAS-USDJPY-M5-001_PREREG.md`
- `research/HYP-VRAS-USDJPY-M5-001_ENGINEERING_AMENDMENT.md`
- `research/HYP-VRAS-USDJPY-M5-001_COST_PREFLIGHT.md`
- `research/HYP-VRAS-USDJPY-M5-001_READOUT.md`
- `research/evidence/HYP-VRAS-USDJPY-M5-001_ENGINEERING/ENGINEERING_RECEIPT.json`
- `research/evidence/HYP-VRAS-USDJPY-M5-001_ENGINEERING/FINAL_COMPILE_RECEIPT.json`
- `research/evidence/HYP-VRAS-USDJPY-M5-001_P0/design_confirmation.json`

Historical HYP-015 preflight artifacts remain immutable audit evidence. Neither
the HYP-015 failure nor this pre-Model0 hold is a market no-edge verdict.
