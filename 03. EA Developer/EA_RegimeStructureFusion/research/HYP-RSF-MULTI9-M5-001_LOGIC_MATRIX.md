# HYP-RSF-MULTI9-M5-001 Logic-to-Code Matrix

## Identity

- EA: `EA_RegimeStructureFusion`
- Entry timeframe: M5
- Context timeframe: M15
- Universe: EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD, NZDUSD,
  XAUUSD and BTCUSD
- Authority: Owner-directed research lane, independent of the sequential T2
  campaign lock; no paper/live authority

## Component ownership

| Component | Responsibility | Must not do |
|---|---|---|
| AIRD | Probabilistic regime, confidence and high-vol state | Generate entries alone |
| VRC | Deterministic trend/range/compression and volatility state | Duplicate QQE timing |
| MBB | S1/S2/S3 setup event and band geometry | Decide structure validity |
| TB SMC | Sweep, BOS/MSS, displacement, zone state and stop anchor | Act as a raw standalone trade |
| QQE | Momentum timing on a completed bar | Override incompatible regime/structure |

## Mode routes

| Mode | Context | Setup | Structure | Timing |
|---|---|---|---|---|
| RANGE long/short | VRC mean-revert/range plus AIRD range probability | MBB S1 | recent opposite-side TB sweep/reclaim | QQE reverses from an extreme |
| TREND long/short | AIRD and VRC direction agree | MBB S2 | TB bias plus BOS/MSS or active same-side cell/void | QQE stays/reaccelerates on the correct zero side |
| BREAKOUT long/short | prior VRC compression/low-vol or MBB release | MBB S3 | same-side TB displacement and BOS/MSS | QQE momentum agrees |

Breakout is evaluated first because release events are short-lived. Trend is
second. Range is last. Failure of one route does not silently fall through to
the opposite direction.

## Non-repaint contract

- `OnTick` uses bar zero only to detect the opening of a new M5 bar.
- AIRD/VRC context buffers are read at M15 shift 1/2.
- MBB/TB SMC/QQE buffers are read at M5 shift 1 or older.
- Recent structural events scan only shifts `1..InpStructureEventMaxAgeBars`.
- The TB SMC ready flag and public contract version must pass before a decision.
- Server-side SL/TP remains tick-accurate; entries and discretionary time exits
  do not use forming-candle indicator values.

## Risk and execution

- Stop distance is the maximum of MBB half-width, minimum ATR floor, broker
  stop level, 3x live spread and the applicable TB structural anchor plus ATR
  buffer.
- Stops wider than the declared ATR cap or with excessive spread/stop ratio are
  rejected.
- Position size is calculated from loss at the initial stop and can only be
  reduced for free-margin safety.
- High-volatility is a risk scalar, not a universal veto.
- One owned symbol position, no foreign-magic symbol position, daily/account
  equity locks, entry cooldown, max trades/day, max hold and Friday flat apply.

## Optimization boundary

AUTO symbol profiles provide outcome-blind session/mode priors only. Any
economic search must use the frozen block order and full-trial accounting in
the preregistration. No parameter value in the source is labelled optimal.

## EURUSD Block-1 outcome

`HYP-RSF-EURUSD-M5-BLOCK1-001` completed all 18 preregistered discovery cells
and produced no survivor. The synchronous route matrix is therefore an
engineering reference, not a validated trading rule. Its complete failure
packet is under `research/block1/`; no parameter rescue or cross-symbol
parameter transfer is authorized.
