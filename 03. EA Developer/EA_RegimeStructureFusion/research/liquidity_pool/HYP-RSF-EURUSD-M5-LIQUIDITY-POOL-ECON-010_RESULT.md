# HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010 — terminal result

## Verdict

`KILL_BASE_ECONOMICS_NO_PARAMETER_RESCUE`

The causal unconsumed-swing liquidity-pool implementation is engineering-valid,
but the frozen EURUSD M5 trading object has negative expectancy after the native
Strategy Tester costs. It is not worth parameter rescue. Validation, holdout,
optimization, CPCV/WFA, Monte Carlo, paper, promotion and live authority remain
closed.

## Frozen test identity

- EA: `EA_RegimeStructureFusion`
- Run: `20260807_102556`
- Symbol/timeframe: EURUSD / M5
- Window: 2018-01-01 through 2022-12-31
- Model: MT5 Model 0, every tick
- Deposit/leverage: USD 100,000 / 1:100
- Trial count: one preregistered development trial; no optimization
- EA source SHA256: `05D13CAF75B05D3B2585493734B3E315BFCB84004BFB989D228E08B0C79C257A`
- TB source SHA256: `3848CBD4FD34748BE95A372D4797465383CC7EDDE0ED36687E8AA26546893539`

## Economic result

| Metric | Result | Gate |
|---|---:|---:|
| Trades | 162 | diagnostic population |
| Net profit | -USD 3,981.17 | positive required |
| Profit factor | 0.714519 | >= 1.30 required |
| Win rate | 38.30% | diagnostic |
| Max drawdown | 4.9005% | <= 8% passed alone |
| Expectancy | -USD 24.58/trade | positive required |
| Mean achieved R | -0.136032R | positive required |
| Median achieved R | -1.017743R | diagnostic |

Drawdown passing does not compensate for negative expectancy or PF below one.

## Session and engine diagnosis

No preregistered session produced positive economics:

- Europe: 112 trades, PF 0.68, net -USD 3,274.
- New York: 50 trades, PF 0.80, net -USD 707.

The engine decomposition is diagnostic only and cannot authorize pruning:

| Engine | Trades | Net | PF | Mean R |
|---|---:|---:|---:|---:|
| Breakout long | 42 | +USD 671.52 | 1.2592 | +0.0149R |
| Breakout short | 35 | -USD 1,347.51 | 0.5825 | -0.2880R |
| Trend long | 36 | -USD 1,075.99 | 0.6632 | -0.1611R |
| Trend short | 49 | -USD 2,229.19 | 0.5481 | -0.1384R |

The breakout-long slice is a post-outcome subset, remains below the frozen PF
gate, and has near-zero mean R. Selecting it would be post-hoc overfitting.

## Structural funnel and reconciliation

- Closed bars: 372,914; processed ticks: 105,949,201.
- Indicator-ready bars: 123,064; not-ready bars: 0.
- All TB snapshot fail counters: 0.
- Armed/retested/confirmed: 5,349 / 1,647 / 162.
- Expired/cancelled: 1,685 / 3,502.
- Rejected for no live objective: 151.
- Rejected for insufficient objective runway: 914.
- Entries/final closes: 162 / 162.
- EntryContext rows: 162; Lifecycle rows: 324 = 162 OPEN + 162 final CLOSE.
- Minimum accepted objective room: 1.25451061R.
- Wrong-side or below-1.25R accepted objectives: 0 / 0.

This proves the indicator/EA contract, causal objective selection and telemetry
worked as designed. It also proves that correct structure plumbing did not
create an edge.

An independent Grok review confirmed the three-layer verdict and found one P2
engineering debt item: 12/162 entries retained the nearest liquidity objective
captured when the event armed even though a nearer still-live level existed at
entry. All remained on the correct side and above the frozen 1.25R runway, so
this is not repaint/lookahead and does not invalidate the economic kill.
Rebinding at entry would change the decision surface and therefore cannot be
patched and retested as a HYP-010 rescue. See
`HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010_GROK_REVIEW.md`.

## Chart-grounded finding

The native MT5 Visual Mode casebook uses the actual MBB, QQE and TB structural
indicator overlays plus real entry/SL/TP/exit markers. Winners more often show a
protected swing, fresh BOS/MSS, a retest and a usable opposing liquidity
corridor. Losers frequently trigger into nearby opposing supply/demand or after
the structural impulse has degraded into range/compression. These observations
explain failure modes; they are outcome-derived and therefore may not be turned
into filters under HYP-010.

Canonical native screenshots are under:
`03. EA Developer/EA_RegimeStructureFusionForensics/research/visual/native_structural_event_005/`.

The attempted TradingView custom-indicator comparison was blocked by account
sign-in. No TradingView parity claim is made.

## Legal next step

This exact AIRD/VRC context + MBB event + QQE timing + TB structural sequence +
unconsumed-swing objective decision surface is terminal on EURUSD M5. A future
candidate must introduce a materially different causal mechanism, freeze a new
hypothesis before outcomes and re-establish its symbol/timeframe/data/cost
contract. Timezone, direction, engine, RR and threshold mining from this run are
forbidden.
