# HYP-STBS-XAUUSD-M15-008 — frozen Model-0 execution-governance child

## Thesis and identity

HYP008 is a fresh outer execution/evidence identity for the exact byte-frozen HYP007 trade implementation after HYP007 closed before packet build for governance defects only. It makes no signal, parameter, risk, session, direction, stop, target, sizing or lifecycle change.

- Outer hypothesis: `HYP-STBS-XAUUSD-M15-008`
- Inner implementation/log identity: `HYP-STBS-XAUUSD-M15-007`
- EA: `EA_SupertrendBurstScalperTrade`
- Symbol/chart: `XAUUSD/M15`
- Tester preload: `2005.01.01` inclusive to `2023.01.01` exclusive
- Economic DESIGN trades: server time `[2018.01.01 02:00, 2023.01.01 02:00)` only
- Model: MT5 Model 0, execution mode 0, fixed delay 0, current spread
- Deposit/leverage: 10,000 / 100
- Role/profile: control; telemetry `none/off`; empty input overrides
- The source default and hard guard retain inner `InpHypothesisId=HYP-STBS-XAUUSD-M15-007`.

The signal remains closed H1 Supertrend-10x3 flips mapped to the exact next native M15 open, with prior closed M15 ATR14, 1.00 ATR stop, 1.50R target, 0.25% requested-price risk, max eight completed M15 bars, and the frozen durable execution FSM.

## Exactly-once stages

1. A fresh HYP008 `probe` may authorize only `STBS008-PACKET-BUILD-001`, limit one. The builder must create and fsync its exclusive start before reading any bound registry/source/tool/evidence bytes. It must terminalize COMPLETE or FAILED; any failure consumes the ID.
2. Packet completion does not authorize MT5. A reserved post-packet review path is created before sealing and excluded from immutable evidence. Only its bytes may change without changing the Git path set.
3. A later HYP008 `screened` row may authorize only `STBS008-MODEL0-TRAIN-001`, limit one, after independently reviewing and hash-binding the packet, receipt, start/terminal and final review. The launcher must claim before reading AlphaFactory, receipt, registry or any bound artifact.
4. No same-ID retry and no registry mutation from either executable.

## Baseline acceptance and stop rules

The one Model-0 run is a TRAIN falsification, not promotion proof. Over the frozen DESIGN window it must have:

- at least 500 closed trades;
- pooled cadence 2–5 trades/week;
- LONG and SHORT each at least 30%;
- no calendar year above 30% of trades;
- positive net expectancy and PF strictly above 1.30 after tester costs;
- maximum equity drawdown at most 8%;
- no negative calendar year;
- later research stress PF at least 1.25 for x1.5 costs and at least 1.00 for x2 costs.

Any failed gate terminally parks the exact economic object. No post-read filter, direction/session removal, stop/target change, sizing change, parameter search or same-ID retry is allowed. A materially new strategy hypothesis may follow.

Model 0 and the separate historical cost-source manifest are research evidence only. Observed fill slippage is missing, not zero; even a pass cannot authorize OOS, holdout, paper, live or deployment. Those remain locked until a fresh higher-fidelity cost/execution stage is preregistered.

## Forbidden before the screened run row

AlphaFactory, compile, MT5, trade API, outcome prices, post-event OHLC, performance metrics, economics, optimization, validation, holdout, promotion, paper/live, network and paid requests.
