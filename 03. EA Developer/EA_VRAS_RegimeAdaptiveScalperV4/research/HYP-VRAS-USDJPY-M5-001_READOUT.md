# HYP-VRAS-USDJPY-M5-001 final readout

## Outcome

The supplied three-engine EURUSD plan was not implemented literally. Its quoted
structural statistics identify USDJPY, true CVD/VPIN/LOB OFI are unavailable
from the retail OHLCV contract, two proposed engines lacked independent frozen
evidence, and the asynchronous timeout/reset route could duplicate late fills.

The legal successor is one atomic USDJPY M5 Asian-session OU engine. The EA is
complete and engineering-valid, but this exact hypothesis is terminally parked
before Model 0 because same-symbol commission and independent slippage evidence
are absent.

## Outcome-blind P0

Bound source:
`FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/USDJPY/USDJPY_M5_ALL_AVAILABLE_20260801.parquet`

Source SHA256:
`FECD42A01AFD14D4149121A122468DA5597939A20DD1533A36DA711E6FA2DAFD`

- eligible wrapping Asian sessions: 1,286
- median Hurst: 0.42517682
- median VR(5): 0.88361271
- valid OU fraction: 0.98055988
- median half-life: 11.8583 M5 bars, about 59 minutes
- frozen structural gates: 6/6 passed
- trade outcomes accessed: no

## Implemented object

- USDJPY M5, `[22:15,05:30) UTC`
- exactly 72 completed, contiguous bars from one wrapping session
- OLS OU state with `0<b<1`, half-life `[1,36]`, VR(5) `<1`
- entry at `abs(z)>=2`, target OU equilibrium, tail/ATR stop, RR gate `>=1.5`
- matched primary `+1` and reverse control `-1`
- synchronous `OrderCheck` and `OrderSend`; broker SL/TP in the entry request
- 0.25% equity risk, persistent daily/account hard latches, UTC clock contract
- lifecycle-v3 telemetry with partial-fill risk allocation and exact final-close
  reconciliation
- no true-flow proxy relabeling and no multi-engine arbitration

The original preregistration remains byte-stable. Review-derived engineering
clarifications are separately frozen in
`HYP-VRAS-USDJPY-M5-001_ENGINEERING_AMENDMENT.md` before the final compile and
before any MT5 or economic outcome.

## Verification

- source SHA256: `425352144DE7E9F3291D48FEC85C52E0B2F6FDE2FB87BA83CEAACB9EB978EAFE`
- tests: 33 passed, 0 failed
- final compile: 0 errors, 0 warnings
- EX5: 49,650 bytes; SHA256
  `61C9BAADFDC49EAC477523F15BB85430F1DAA282E8F5BCB6ACDFBE078959E332`
- canonical non-repaint audit: PASS, 0 findings
- independent final code review: PASS
- MT5 launches: 0
- economic trials/trades: 0

## Three-layer verdict

1. `engineering-valid`: PASS.
2. `economic-valid`: NOT TESTED; no authority was opened.
3. `promotion-ready`: FALSE.

Terminal registry verdict:
`PARK_PRE_MODEL0_MISSING_USDJPY_COMMISSION_AND_SLIPPAGE_PROVENANCE`.

Any future economic attempt requires hash-bound USDJPY commission and
independent slippage evidence plus a fresh preregistered successor. Assumed
`0.70` commission pips and `0.30` one-way slippage cannot be relabeled verified.
