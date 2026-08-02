# EA_VRAS_RegimeAdaptiveScalperV4

The invalid three-engine EURUSD plan remains closed under
`HYP-VRAS-EURUSD-M5-015`. Its headline Hurst/VR/OU values came from the USDJPY
tail of a combined three-symbol DESIGN file, and its true-flow/estimator/async
contracts were not build-ready.

The package contains the target-symbol-aligned USDJPY M5 Asian OU line:

- USDJPY M5, `[22:15,05:30) UTC`;
- one atomic closed-bar OU mean-reversion engine;
- synchronous tester-only order execution with server SL/TP;
- persistent daily/account risk latches and lifecycle-v3 telemetry;
- no CVD, VPIN, OFI, Volman, sweep, or multi-engine claim.

Current terminal verdict:

`KILL_PRIMARY_MODEL0_ZERO_EDGE_AND_CADENCE_TELEMETRY_CONTRACT_FAIL`

Evidence status:

- HYP-001: P0 6/6 on 1,286 DESIGN sessions and engineering-valid; parked before
  Model 0 because promotion-grade USDJPY cost evidence was absent.
- HYP-002: acquired a research-only spread/commission/quote-latency proxy, but
  was parked before outcome access when the predicted report data fingerprint
  did not match the actual FivePercent tester population.
- HYP-003: identity-corrected single Model 0 primary; source compiled with zero
  errors and the run-bound non-repaint audit passed.
- Economic result: 3 trades over 260.57 elapsed weeks (0.0115/week), 3 losses,
  PF 0.00, net -47.75 USD, expectancy -15.92 USD/trade, DD 0.23%.
- Post-processing also found invalid lifecycle final-close rows (zero volume,
  epoch time), so report-bound proxy repricing could not be built.
- Optimization, validation, holdout, promotion, paper and live: forbidden.

The primary PF/cadence kill is terminal even without the missing repricing:
non-negative cost cannot turn 3/3 losses into PF >1.30, and three trades cannot
meet the frozen 2-5 trades/elapsed-week gate. Do not rescue this exact object by
loosening OU/VR/z/geometry filters, changing the window/session, or reversing
direction after reading the result. A successor needs a materially new mechanism
and a pre-economic lifecycle close-deal fixture; promotion additionally still
needs observed commission/fill evidence.

Start with:

- `research/HYP-VRAS-USDJPY-M5-003_FAILURE_PACKET.json`
- `research/HYP-VRAS-USDJPY-M5-003_FROZEN_PREREG.md`
- `research/HYP-VRAS-USDJPY-M5-002_OPERATIONAL_CLOSEOUT.json`
- `research/HYP-VRAS-USDJPY-M5-002_FROZEN_PREREG.md`
- `research/evidence/HYP-VRAS-USDJPY-M5-002/MODEL0_IDENTITY_PREFLIGHT/DURABLE_EVIDENCE_INDEX.json`
- `research/evidence/HYP-VRAS-USDJPY-M5-002/RESEARCH_COST_PROXY_RECEIPT.json`
- `research/evidence/HYP-VRAS-USDJPY-M5-001_P0/design_confirmation.json`

Historical HYP-015/HYP-001/HYP-002 artifacts remain immutable lineage evidence.
The kill applies only to the exact HYP-003 strategy object, not to USDJPY or
mean reversion in general.
