# HYP-LVOR-EURUSD-M15-002 — Source Feasibility Plan

Status: `FROZEN_PRE_OUTCOME_IMPLEMENTATION_CHILD`

## Identity and exact parent failure

- Hypothesis: `HYP-LVOR-EURUSD-M15-002`
- Parent: `HYP-LVOR-EURUSD-M15-001`
- Attempt: `LVOR002-SOURCE-ATTEMPT-001`, limit exactly one.
- Family: `liquidity-vacuum-overshoot-reversal`.
- Symbol/timeframe: FivePercent public DESIGN EURUSD, M15 decision, immediate
  M5 confirmation, H1 BID volatility.

The parent attempt is terminal at:

`03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/evidence/HYP-LVOR-EURUSD-M15-001_SOURCE_FEASIBILITY_ATTEMPTS/LVOR001-SOURCE-ATTEMPT-001/attempt_terminal.json`

Its SHA256 is
`F0CFC1AE6496E0C3799CA5D424A8E2F2DA3271971CE97BB5ACCD1CDB67D62384`.
It records `ENGINEERING_INVALID_NO_MARKET_VERDICT`, attempt
`LVOR001-SOURCE-ATTEMPT-001`, and exact reason `ContractError` /
`forbidden outcome field: complete_m15_plus_following_m5`. Its artifact chain
contains only `attempt_started.json` SHA256
`D7109B7ACA72B6639C8E3271E858EF8B284C017A252310AD9A83A0FCE52C62EA`.
No report, ledger, source count, Stage-0 result or economic outcome was emitted.
The parent cannot be rerun.

## Only authorized implementation repair

The parent report used the pre-decision formation field name
`complete_m15_plus_following_m5`. The generic outcome-blind guard correctly
retains the forbidden token `win`, which appears accidentally inside the word
`following`; therefore report persistence failed before any source result.

This child changes only that report key to
`formed_m15_plus_confirm_m5`. The value and calculation remain the count of
complete eligible M15 bins with the exact immediately following complete M5
confirmation. Forbidden tokens and outcome protection are not weakened:
explicit win, loss, return, PnL, profit, trade, MFE, MAE, target-hit, stop-hit
and post-entry fields remain fatal.

## Mechanism and source contract unchanged

Every semantic market/data/risk/gate rule from the frozen parent is retained:

- Public DESIGN `2016-01-04..2020-12-31`; validation, holdout, private and
  sealed branches remain closed.
- Monday-Friday M15 starts `>=06:00` and `<18:00` UTC, exact 15 consecutive M1
  rows; confirmation is the exact immediately following complete five-row M5;
  decision time is confirmation close.
- Closed shift-1 H1 BID Wilder ATR20.
- Broker tick-volume activity proxy equals current M15 volume divided by the
  median of the same UTC slot on exactly 20 prior business dates.
- Frozen falsification priors: `A <= 0.85`, range/ATR `0.50..1.25`, impulse
  efficiency `>=0.70`, directional close in its outer 20%, opposite M5 body
  closing beyond the M15-body midpoint; direction opposite the impulse; first
  candidate per UTC business date.
- PRICE_ONLY removes only activity. SHIFTED_ACTIVITY uses the fully as-of
  same-slot activity ratio from exactly five business dates earlier. Controls
  are diagnostic only.
- Future risk remains fixed SL `1.0 * ATR20`, `0.20%` risk, no TP/BE/trail/
  partial, six complete observed M5 time exit. Source mapping remains timestamp
  only: first observed M1 at/after decision within 60 minutes and six complete
  M5 timestamps. Cost geometry remains `1.50 pip / ATR20_pips`.
- PRIMARY Stage-0 gates remain cadence `2..5` per 260.5714285714 elapsed weeks,
  at least 25% and 20 observations each direction, no year over 30%, formation
  and executable ratios at least 99%, median cost/SL ratio at most 0.25.
- Thresholds remain preregistered priors without direct literature calibration;
  tick volume remains a broker proxy. Source PASS is not edge evidence.
- O(N) one-time immutable timestamp/activity indexes and bisect-only per-signal
  horizon mapping remain mandatory.

No threshold, control, session, direction, horizon, risk, gate, source hash or
data permission may change after the first source read. A fail kills this exact
child only. A pass authorizes only a separately preregistered future economics
decision, never MQL5/MT5.

## Parent-bound canonical authority and durability

Before receipt, clock, reservation or any DESIGN metadata, execution must
validate the exact latest canonical HYP002 registry row and stable-read/hash/
strict-validate the exact parent terminal above. The row must bind the parent
terminal path and SHA. Parent identity, attempt, terminal status, exact reason,
one-artifact chain, zero outcome/economic counters and literal-false sealed
permissions are mandatory. Parent validation supplies no rerun authority.

The exact canonical HYP002 implementation review receipt must bind this plan,
the normalized disarmed builder and exact tests. Then the clock must pass and
the exact new evidence root must be reserved atomically:

`03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/evidence/HYP-LVOR-EURUSD-M15-002_SOURCE_FEASIBILITY_ATTEMPTS/LVOR002-SOURCE-ATTEMPT-001`

Durable O_EXCL artifacts remain STARTED, outcome-blind report, flattened
three-arm ledger, source-feasibility receipt and terminal. Post-reservation
failure produces `ENGINEERING_INVALID_NO_MARKET_VERDICT`; Stage-0 pass maps to
`PASS_SOURCE_FEASIBILITY`, otherwise `SOURCE_FAIL_NO_ECONOMICS_AUTHORITY`.

The sentinel remains exactly
`REVIEWED_REGISTRY_ROW_SHA256: str | None = None`. This implementation task
does not arm/run, create receipt/registry/evidence, or open DESIGN. Economics,
outcomes, performance, validation/holdout/private/sealed, network/paid,
optimization/charting, MQL5/MT5, promotion, paper and live remain forbidden.
