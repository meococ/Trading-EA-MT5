# PREFLIGHT PLAN — HYP-VRAS-EURUSD-M5-015

Status: FROZEN on 2026-08-02 before executing the corrected data-identity
probe, opening any trade outcome, creating MQL5 strategy source, or launching
MetaTrader Strategy Tester.

This is a one-use, outcome-blind plan review. Any changed estimator, symbol,
data source, decision surface, or gate after reading the result requires a new
hypothesis ID.

## 1. Identity and authority

- Hypothesis: `HYP-VRAS-EURUSD-M5-015`
- Proposed package: `EA_VRAS_RegimeAdaptiveScalperV4`
- Requested implementation target: FivePercent `EURUSD`, M5.
- Owner scope: review and implement the supplied `final_ea_build_plan.md`.
- Supplied plan SHA256:
  `453E8EC25F5C79BCEBBF598D2394AA7E3112531366AA7E7A7C9D72F7B4653B9C`.
- Supplied empirical report SHA256:
  `5A053AEDC8DC9562E2264F0456AC363A00EA3ECB5D0966644BC934DCEBB38587`.
- Original empirical runner SHA256:
  `E77C29139BB2B1D1A178639381306D77E7E0A631C2773CB13041BA47C6FBD663`.
- Current authority: repair the empirical runner, add synthetic tests, and
  execute exactly one data-identity/capability preflight.
- `.mq5`, compile, Model 0/4, economics, optimization, validation, delivery,
  paper, and live authority are conditional on every preflight gate passing.
- This is a temporary Owner-directed P0 review exception. It does not consume
  T2 economic exposure and does not transfer T2 build/MT5 authority unless this
  preflight survives and a later campaign amendment explicitly does so.

## 2. Bound sources and sealed data

Claimed EURJPY evidence source:

- Parquet:
  `02. AlphaFactory/data/fivepercent/TriangularConsensusLag/HYP-TRILAG-EURJPY-M1-002/design_m1_close.parquet`
- Parquet SHA256 declared by its canonical manifest:
  `C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6`.
- Manifest:
  `02. AlphaFactory/data/fivepercent/TriangularConsensusLag/HYP-TRILAG-EURJPY-M1-002/design_m1_manifest.json`
- Manifest SHA256:
  `4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8`.
- The manifest is authoritative for symbol membership, row counts, design
  years, and sealed years. The probe may load only the declared 2016–2020
  DESIGN parquet; it must not load the sealed 2021–2024 validation data.

Target EURUSD capability source:

- Manifest: `02. AlphaFactory/data/fivepercent/EURUSD/manifest.json`.
- Manifest SHA256:
  `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`.
- The preflight may inspect manifest/schema facts only. It must not compute
  forward outcomes, PnL, PF, MFE/MAE, or open the 2023+ holdout.

## 3. Exact reproduction and corrected checks

The runner must report both the legacy failure and the corrected result:

1. Reproduce the original unfiltered `tail(10,000)` Hurst/VR and
   `tail(1,440)` AR(1)-OU calculation so the supplied numbers can be traced.
2. Report the symbol of every row used by that unfiltered tail.
3. Filter `symbol == EURJPY` before reproducing the same metrics.
4. Separately filter `symbol == EURUSD`, because EURUSD is the proposed EA
   target and cross-symbol transfer is not evidence.
5. Compare observed symbol rows and time coverage with the canonical manifest.
6. Session diagnostics must be partitioned by UTC calendar day. Disjoint
   sessions may not be concatenated across overnight gaps before Hurst, VR, or
   OU estimation.
7. The legacy estimator is reproduced only for forensic parity. Its point
   estimates do not authorize fixed Hurst/VR/OU thresholds because the supplied
   plan declared no estimator confidence interval, null calibration, power,
   or rolling stability contract.

## 4. Flow-data and execution capability checks

The plan requires causal `VPIN`, `CVD`, and `OFI`. The gate passes only if the
bound target source supplies all required decision-time primitives:

- signed/aggressor-classified trade volume for CVD;
- volume buckets plus signed trade volume for VPIN;
- synchronized bid/ask queue sizes (or an independently specified equivalent)
  for LOB OFI.

`tick_volume`, candle direction, OHLC, simulated Model-0 ticks, and BBO prices
without queue size do not pass. A proxy may become a different future
hypothesis only after its exact signing, bucket, missingness, fidelity, and
Model-4/forward-collection contract is frozen; it may not be called true order
flow.

The async gate also fails unless a production kernel has durable intent,
restart recovery, request/deal/order/position correlation, partial/late-fill
fixtures, foreign-ownership tests, and a timeout state that remains ambiguous
instead of resetting to `IDLE`. The current shared kernel is compile-only and
mutation-disabled, so it cannot satisfy this plan's prop-ready claim.

## 5. Frozen gates and verdict routing

All must pass before any V4 EA source is authorized:

1. Exact requested-symbol filter is applied before every statistic.
2. Claimed row count and history coverage match the canonical manifest.
3. The supplied headline EURJPY values are actually computed from EURJPY rows.
4. EURUSD has its own pre-outcome estimator/stability evidence; EURJPY or
   USDJPY statistics are not transferred.
5. True VPIN/CVD/OFI primitives exist for the proposed backtest/live contract.
6. Hurst/VR/OU estimators, windows, significance/power, engine arbitration,
   clock, costs, and matched control are fully defined.
7. The execution kernel meets the production async contract.

Any failure yields:

`PARK_PRE_EA_INVALID_PLAN_EVIDENCE_OR_CAPABILITY_NO_OUTCOME_READ`

That verdict authorizes no `.mq5`, compile, Strategy Tester launch, parameter
repair, alternative symbol, or post-result proxy substitution. It is an
engineering/evidence verdict, not a market no-edge conclusion.

## 6. Trial accounting and required artifacts

- One deterministic preflight; trial universe `N=1`.
- No parameter grid, alternative estimator, threshold, symbol transfer, or
  economic arm.
- Required: red-first/pass test receipt, corrected runner hash, JSON result,
  human readout, failure packet, registry transitions, and documentation update.
- Every artifact must state that outcomes/economics were not opened and that
  promotion eligibility is false.
