# New Strategy Deep Research Packet — 2026-07-12

Status: `PRE-RESEARCH / NOT PREREGISTERED / NO EA CODE AUTHORIZED`

## Purpose

Find one genuinely new, testable intraday FX strategy mechanism for a new MQL5
EA. The result is research input only. It must survive local de-duplication and
an offline population probe before any hypothesis is registered, frozen, or
implemented.

## Workspace objective

- Profit factor strictly above 1.30 after verified full cost at x1.
- Cost stress: PF at least 1.25 at x1.5 cost and at least 1.00 at x2 cost.
- Cadence: 2-5 trades per elapsed calendar week in train and holdout.
- No weekend exposure; avoid overnight exposure where the mechanism permits.
- Closed-bar, non-repainting decisions only.
- Capital preservation and stable out-of-sample expectancy outrank in-sample PF.

## Available implementation universe

- MetaTrader 5 / MQL5, AlphaFactory Model 0 for meaningful controls.
- Canonical unsuffixed FX symbols currently include EURUSD, GBPUSD, XAUUSD;
  USDJPY is allowed only under an explicitly frozen contract.
- M5/M15 are preferred for intraday execution. Higher timeframes may be
  closed-bar context only.
- Current same-broker cost evidence is incomplete: never interpret missing or
  zero spread, commission, slippage, swap, or fee as free execution.

## Local failure catalog to de-duplicate against

Do not merely rename or threshold-tune these exhausted/failed families:

- London/Asian range stop-hunt, sweep/reclaim, session-only reversal, and
  generic opening momentum/drift.
- Sonic Classic/PVSRA/Dragon/Trend threshold filters, ATR impulse filters,
  compression filters, HTF sweep/velocity filters, and context-fail rescue.
- Gap fill after historical entry spread and rollover costs.
- Fixed-target other-pair lead-lag, same-bar USD consensus, laggard catch-up,
  and strongest-pair common-USD factor routing without valid cost provenance.
- MFE/BE/TP/max-hold management rescue as a substitute for a new entry edge.
- Calendar/hour/day/year veto mined from prior outcomes.

Existing catalog truth: 217 identity-valid non-empty runs across 34 EAs
contained zero runs meeting both PF > 1.30 and 2-5 trades per elapsed week.

## Research task for ChatGPT

Use `Sol 5.6`, effort `xhigh`, and `Deep Research`. Prefer primary sources:
peer-reviewed papers, central-bank/BIS research, exchange or broker
specifications, and official market microstructure documentation. Forums may
identify trader context but cannot establish edge.

Return:

1. Three candidate mechanisms that are materially distinct from the local
   failure catalog. Explain the economic or microstructure mechanism and why it
   could persist after realistic retail-CFD costs.
2. A source table with title, author/publisher, date, URL, accessed date, and
   whether each item supports a fact, inference, or suggestion.
3. Exact closed-bar rules for entry, side, exit, stop, target, time stop,
   session/timezone, conflict arbitration, warmup, missing-data behavior, and
   next-bar executable-price convention.
4. Source-backed default parameters. Keep the total research degrees of
   freedom small and list every parameter/trial explicitly.
5. Expected regime, failure modes, execution risks, broker constraints, and
   reasons the strategy may disappear in MT5 retail data.
6. A de-duplication matrix against every failed family listed above.
7. Rank the three candidates using mechanism independence, expected cadence,
   cost tolerance, data availability, implementation complexity, and
   falsifiability. Do not rank by hypothetical profit.
8. For the top candidate, define one cheap offline population probe using
   existing OHLC/tick artifacts, with frozen train and one-time holdout,
   conservative costs, exact pass/kill gates, sample-size gates, year/regime
   concentration gates, and no post-result rescue.
9. Provide one MQL5 build contract only after the probe section: modules,
   indicators/data access, shift discipline, position/risk model, symbol
   geometry, telemetry, and non-repaint audit points. Do not generate EA code.

## Mandatory rejection rules

Reject a candidate before code if it requires lookahead, unavailable
bid/ask/order-book data, event timestamps that cannot be aligned historically,
zero/missing cost assumptions, discretionary chart reading without a frozen
label contract, more than a small preregistered trial budget, or post-hoc
session/threshold rescue.

The research answer does not authorize a registry row, prereg freeze, EA edit,
compile, backtest, or promotion. Local artifact checks and the offline probe
remain authoritative.
