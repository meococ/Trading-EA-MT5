# HYP-STBS-XAUUSD-M15-007 — sole Model-0 TRAIN falsification preregistration

Preregistered at: `2026-08-09T07:48:00Z`

## Frozen object

- Exact source SHA256: `2E0501CC0C19A8FD8418242A0EC64D725EBC14425AD7A1718F9FEB444B977E32`.
- Exact EX5 SHA256: `8D8B2B3E66DFA1FE8E3C724DFDC8D2FFED529ECD9FFABA871E3993BEAE9DAACC`.
- Symbol/chart: FivePercent `XAUUSD`, native `M15`.
- Tester preload: `2005.01.01` through `2023.01.01`; source itself emits/trades only server-time `[2018.01.01 02:00, 2023.01.01 02:00)`.
- AlphaFactory: Model `0`, execution mode `0`, fixed delay `0`, current spread, deposit USD 10,000, leverage 1:100, control role, telemetry profile `none`/tier `off`, empty overrides.
- One baseline attempt only. No optimization, parameter search, session/direction filter, stop/target change or retry under this identity.

Model 0 is a cheap TRAIN falsification screen, not promotion-grade fill evidence. Historical spread and commission proxy evidence are bound; observed fill slippage is missing and must not be imputed as zero. A survivor still requires separately frozen higher-fidelity cost stress and forward execution evidence.

## Baseline gates

Evaluated only over trades entered in the frozen 2018–2022 DESIGN window:

- at least 500 completed trades and calendar cadence between 2 and 5 per week;
- LONG and SHORT each at least 30%; no calendar year above 30% of trades;
- MT5-reported net expectancy positive, profit factor strictly greater than 1.30 and max equity drawdown at most 8%;
- no year with negative net expectancy;
- later ledger cost stress must retain PF at least 1.25 under 1.5× total observed/proxy cost and at least 1.00 under 2× cost.

Any baseline gate failure kills only this exact trade mapping and immediately triggers independent post-failure review plus a fresh hypothesis/research loop. It does not cancel the owner goal. Passing opens cost-harness hardening only; it does not open OOS, holdout, paper or live trading.
