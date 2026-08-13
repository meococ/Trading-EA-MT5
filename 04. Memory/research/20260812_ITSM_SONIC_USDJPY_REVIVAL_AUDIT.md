# EA_ITSM Sonic USDJPY revival audit - 2026-08-12

Status: `KILL_NO_REVIVAL`

Scope: artifact-only audit of the archived Sonic R EMA-wave/pullback lineage.
No new backtest, outcome-driven filter, optimization, paid call, Git action,
paper authorization or live authorization was opened.

## Decision

`EA_ITSM` is historically engineering-valid for the tested closed-bar variants,
but it is not economic-valid and cannot lawfully re-enter the active goal.

The unselected 2021-2025 mappings fail the frozen goal PF and/or cadence gates.
The apparently stronger T10/skip-H17 child was selected after a documented
14-run confluence sweep, fails the cadence gate, decays materially in recent
years, and has no identity-bound dynamic spread/commission/slippage evidence.
Running the same family again would be post-hoc revival, not new research.

## Source and engineering evidence

- Snapshot source:
  `02. AlphaFactory/runs/EA_ITSM/20260714_192116/snapshot/source/EA_ITSM.mq5`
- Source SHA256:
  `6B433FC9FB7C8745E90B306DEAFFF2C28F182AE1003FB11AE66E324A0946FCE0`
- Archived EX5 SHA256:
  `D4E8B2EAB4F172E3AD1A2CA71DE859569E4F0EB6DF88BFB04521A2CDA2C4925B`
- Archived compile log reports `0 errors, 0 warnings`.
- Entry and optional filter decisions use `CopyBuffer(..., shift=1, ...)` or
  `iOpen/iHigh/iLow/iClose(..., shift>=1)` on a new-bar gate. The only bar-zero
  read is `iTime(...,0)` for new-bar detection. The actually tested strict
  siblings have HTF/MACD/RSI/ADX disabled, so no enabled MTF alignment path is
  involved.

Engineering verdict: `PASS_HISTORICAL_ONLY`. This does not establish current
broker identity, data identity, execution quality or economics.

## Independent 2021-2025 siblings

All three unique reports are USDJPY M15, Model 0, current tester spread and
`99%` History Quality. Their trade ledgers record zero commission and tester
slippage is zero.

| Mapping | Run | N | PF | DD | Trades/week | Recent weakness |
|---|---:|---:|---:|---:|---:|---|
| Baseline London+NY | `20260714_003635` | 852 | 1.1567 | 8.93% | 3.27 | 2023 PF 0.9952; 2024 1.1104; 2025 1.0972 |
| StrictAlign NY-only | `20260714_191845` | 540 | 1.2210 | 6.59% | 2.07 | 2023 PF 0.8586; 2025 1.0624 |
| StrictAlign London-only | `20260714_192116` | 482 | 1.1179 | 6.96% | 1.85 | 2023 PF 0.9869; 2025 0.9979 |

The baseline and NY-only mappings meet cadence but fail PF before adding a
real commission/slippage contract. The London-only mapping fails both PF and
minimum cadence. Because these are already upper-bound tester economics, a
new cost receipt cannot turn them into goal survivors.

Report SHA256 values:

- baseline: `97D3B57DB9269DAA930C58E34A27A675C51A8388292846F8C22F918983C3B079`
- NY-only: `27B1D4B729A5596B2486C587BA6592A49EC820F617495385DCD56EC3DAEFA880`
- London-only: `3EABB4F58F2793D95D6FFB1EE181A5B7132008DF6D9F453A2F7D01D9DA0B5114`

## Selected T10/skip-H17 child

The legacy strategy ledger records a 14-run confluence sweep before selecting
ADX20 + H4 bias + weekday exclusions and then removing hour 17. The artifact
representative `20260621_172759` reports:

- N `363`, PF `1.5778`, DD `1.34%` over 2018-2025;
- only `0.87` trades per elapsed week, below the required `2-5`;
- 2024: N `48`, PF `1.0579`;
- 2025: N `45`, PF `1.2997`;
- WFA has only `3/5` profitable OOS windows, despite the wrapper's generic
  `5/5 PASS` tool-completion summary;
- equity audit is `WARN`: top 5% of trades contribute `70.1%` of profit and the
  longest flat period is `495` days;
- the cost stress subtracts an arbitrary USD `0.50` per trade while declaring
  `spread_points=0`, `slippage_points=0`, `commission_round_turn=0`;
- no broker, server, account or data fingerprint binds the result to a
  deployable execution contract.

Therefore the validation wrapper's green status is engineering completion of
five analyzers, not proof that the selected strategy is promotion-ready.

Bound artifact hashes:

- manifest: `A4E1986533AF539D15C9FD1199869297907F5BCDBA526C6C24C20D1B1D3A8135`
- report: `0A4A6E12226A1EF60EEA7F851D7E8BC6A5BCD1AB6D234D413FD7E80827811E8D`
- validation summary: `3EF4BA086203185ABD2C6FA5F4FE4BD31E734A60031DB2488E2F2119B431ABBF`
- WFA: `78AE523F43FF024799C32E95149D9528F48CF6E0CED0DF196668B096F98B2C38`
- equity audit: `7260723AECA8A1C165C9CA14D638987D512F139D0DB32878FAB2ED3E7661DBD6`
- cost stress: `A295A837CDA3B68FA5E4D8A74A381FA1565AF57AF308A4F4646688900825A1F8`

## Grok bounded review

Grok was given the local counts and hashes as an advisory reviewer only. It
returned:

- `ENGINEERING=PASS_HISTORICAL_ONLY`;
- `ECONOMIC=FAIL`;
- `REVIVAL=KILL_NO_REVIVAL`;
- `NEXT=NO_CANDIDATE_LOCAL_FRONTIER`.

Local artifacts above remain the decision authority.

## No-revival boundary

Do not rerun this family by changing EMA periods, session/hour, weekday,
ADX/H4/MACD/RSI, body/touch thresholds, R:R, stop, time exit, sizing, symbol or
timeframe. A future Sonic-based candidate must introduce a materially new,
causal, PIT-verifiable information object; reusing neutral MT5 execution/risk
plumbing is allowed only after that new source object passes its own frozen
source gate.
