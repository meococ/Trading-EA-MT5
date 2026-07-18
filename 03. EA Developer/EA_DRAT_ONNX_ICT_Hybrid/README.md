# EA_DRAT_ONNX_ICT_Hybrid

Status: `KILLED_AT_OFFLINE_PROBE` — no EA source/ONNX export/compile/Model 0
authority under `HYP-DRAT-ONNX-ICT-M15-EUR-001`.

This package implements the DRAT brief as a mechanism independent from the
killed `EA_HybridICT_Sonic` lane:

- two tabular ONNX gates: persistent regime and breakout event;
- causal M15 liquidity sweep -> MSS/CHOCH -> FVG/OB retest state machine;
- H1/H4 directional context, money-risk sizing and fail-closed execution;
- no Dragon, PVSRA, Sonic Wave or post-hoc session rescue.

Canonical hypothesis:
`HYP-DRAT-ONNX-ICT-M15-EUR-001`.

Research evidence lives under `research/`. The raw training bars remained
in-memory and were not retained. The frozen OOS probe produced cadence but a
losing rules-only control (PF 0.7642) and a slightly worse ONNX-gated challenger
(PF 0.7488), so the package stopped before source build and Strategy Tester.

The follow-up independent-frontier audit is
`research/20260716_DRAT_INDEPENDENT_FRONTIER_AUDIT.md`. It closes the local
Gold->USDJPY alternative with a Mon/Thu-unfiltered Model 0 result (PF 0.97,
N=931) and records the minimum external options/order-flow data contract needed
before any fresh DRAT hypothesis can be opened.

Owner selected the EUR/USD options lane and registered Databento on 2026-07-16.
The amended cost-bounded `GLBX.MDP3` definition/statistics acquisition contract
is frozen at
`research/20260716_CME_EURUSD_OPTIONS_ACQUISITION_CONTRACT.md`. Current state is
`DATABENTO_ACCOUNT_REGISTERED_API_KEY_NOT_CONFIGURED`: the SDK/runtime and
pre-charge planner are ready on `D:`, but no paid request or outcome inspection
has occurred. There is still no fresh hypothesis or EA build authority.
