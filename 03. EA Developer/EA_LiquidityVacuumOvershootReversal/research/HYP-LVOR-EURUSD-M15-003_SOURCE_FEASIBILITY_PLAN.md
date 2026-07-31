# HYP-LVOR-EURUSD-M15-003 — Source Feasibility Plan

Status: `FROZEN_PRE_OUTCOME_IMPLEMENTATION_CHILD`

## Identity and parent failure radius

- Hypothesis: `HYP-LVOR-EURUSD-M15-003`
- Parent: `HYP-LVOR-EURUSD-M15-002`
- Attempt: `LVOR003-SOURCE-ATTEMPT-001`, limit exactly one.
- Family: `liquidity-vacuum-overshoot-reversal`.
- Symbol/timeframe: FivePercent public DESIGN EURUSD, M15 decision, immediate
  M5 confirmation and H1 BID volatility.

HYP002 is terminal with no market verdict. Its immutable bindings are:

- Plan SHA256: `C9B32B9D381E244B6287D2F50E773294A7B18407ED56A3A6FA35B801D1ABF414`
- Reviewed builder base SHA256:
  `F710EFED11B88E3614D6092C4B78A11EAD81960CE53551D9D994E6A23F9A09FB`
- Reviewed authority-row SHA256 including LF:
  `56A6BC459C04BAE598632113AC7AD9F10BD7A0A97CF7DB71B53FE4CB241B7D63`
- Started artifact:
  `03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/evidence/HYP-LVOR-EURUSD-M15-002_SOURCE_FEASIBILITY_ATTEMPTS/LVOR002-SOURCE-ATTEMPT-001/attempt_started.json`
  SHA256 `5ABE90BFBF5777004F9058F74509E3BD212919E9DFE9C5F70A801728BC341F2B`
- Terminal artifact:
  `03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/evidence/HYP-LVOR-EURUSD-M15-002_SOURCE_FEASIBILITY_ATTEMPTS/LVOR002-SOURCE-ATTEMPT-001/attempt_terminal.json`
  SHA256 `283EAF1BD92F79247CA5111DD447C44FCB6656C5FD1032E8D19D25A01498ACDA`
- Terminal status: `ENGINEERING_INVALID_NO_MARKET_VERDICT`.
- Exact reason: `ContractError` /
  `forbidden outcome field: FOLLOWING_M5_INCOMPLETE`.

Only STARTED and terminal exist. HYP002 persisted no source report, ledger,
source count, Stage-0 result or economic observation. It therefore supplies no
market evidence and cannot be rerun.

## Only authorized implementation repair

The report ineligibility counter used the diagnostic reason key
`FOLLOWING_M5_INCOMPLETE`. The outcome-blind guard intentionally forbids the
substring `win`; it therefore rejected the diagnostic word `FOLLOWING` before
report persistence.

This child changes only that executable/report/test diagnostic key to
`CONFIRM_M5_MISSING`. Its increment condition and count remain identical: an
otherwise eligible complete M15 has no exact immediately following complete M5
confirmation. The outcome guard is not weakened. Genuine outcome or lifecycle
fields containing win, loss, return, PnL, profit, entry, exit, post-entry,
trade, MFE, MAE, target-hit or stop-hit remain fatal.

This is an implementation-only repair, not post-hoc tuning or market rescue.

## Market, data, control, risk and gate semantics unchanged

Every HYP001/HYP002 trading semantic remains frozen:

- Public DESIGN `2016-01-04..2020-12-31`; validation, holdout, private and
  sealed branches remain closed.
- Monday-Friday M15 starts `>=06:00` and `<18:00` UTC from exactly 15
  consecutive M1 rows; confirmation is the exact immediately following
  five-row M5; decision time is confirmation close.
- Closed shift-1 H1 BID Wilder ATR20.
- Broker tick-volume activity proxy: current M15 volume divided by median same
  UTC slot on exactly 20 prior business dates.
- Frozen falsification priors: `A <= 0.85`, range/ATR `0.50..1.25`, impulse
  efficiency `>=0.70`, directional close in the outer 20%, opposite M5 body
  closing beyond M15-body midpoint, direction opposite impulse, first candidate
  per UTC business date.
- PRICE_ONLY removes only activity. SHIFTED_ACTIVITY uses the fully as-of
  same-slot activity ratio from exactly five business dates earlier. Controls
  remain diagnostic only.
- Future risk remains fixed SL `1.0 * ATR20`, `0.20%` risk, no TP/BE/trail/
  partial and six complete observed M5 time exit. Source mapping remains
  timestamp-only, with first observed M1 within 60 minutes and six complete M5
  timestamps. Cost geometry remains `1.50 pip / ATR20_pips`.
- PRIMARY Stage-0 gates remain cadence `2..5` over 260.5714285714 elapsed
  weeks, at least 25% and 20 observations per direction, no year above 30%,
  formation and executable ratios at least 99%, and median cost/SL at most
  0.25.
- O(N) immutable indexes, strict receipt/registry/parent authority, atomic
  one-use reservation and O_EXCL durable artifact chain remain unchanged.

Thresholds remain uncalibrated falsification priors and tick volume a broker
proxy. Source PASS would not establish edge. No threshold, session, control,
direction, horizon, risk, gate, source hash or data permission may change after
the first source read.

## HYP003 authority and durability

The exact latest canonical HYP003 registry row must bind HYP002 as parent and
bind the exact terminal path/SHA above. Execution must validate canonical row,
then stable-read/hash/strict-validate the exact HYP002 terminal identity,
attempt, reviewed-row SHA, reason, one-artifact chain, zero outcome/economic
counters and literal-false sealed permissions before HYP003 receipt, clock,
reservation or any DESIGN metadata.

The exact HYP003 receipt must use canonical `v1_plan` and bind this plan,
normalized disarmed builder and exact tests. New evidence root:

`03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/evidence/HYP-LVOR-EURUSD-M15-003_SOURCE_FEASIBILITY_ATTEMPTS/LVOR003-SOURCE-ATTEMPT-001`

The sentinel remains exactly
`REVIEWED_REGISTRY_ROW_SHA256: str | None = None`. This task does not create a
review receipt or registry row, arm/run, create evidence, or open DESIGN.
Economics/outcomes/performance, validation/holdout/private/sealed, network/
paid, optimization/charting, MQL5/MT5, promotion, paper and live remain false.
