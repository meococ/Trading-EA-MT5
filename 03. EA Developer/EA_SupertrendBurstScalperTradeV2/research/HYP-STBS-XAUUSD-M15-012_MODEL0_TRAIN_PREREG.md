# HYP-STBS-XAUUSD-M15-012 — untuned Model-0 TRAIN baseline

Status: `FROZEN_PRE_OUTCOME`

## Market thesis and unchanged implementation

H1 Supertrend-10x3 regime flips may retain short-horizon continuation after the exact next native M15 open. The implementation uses the prior completed M15 ATR14 for a 1.00 ATR protective stop, a 1.50R target, 0.25% requested-price equity risk, a maximum eight completed-M15-bar hold, one position, no pyramiding, no trailing/breakeven, a Friday 18:00 UTC entry cutoff and a 20:00 UTC/weekend flatten rule.

HYP012 is the first economic child after HYP011 closed full audit parity. It changes no source byte, signal, side, filter, session, stop, target, sizing, lifecycle or indicator parameter.

- Outer evidence identity: `HYP-STBS-XAUUSD-M15-012`.
- Inner MQL/journal identity: `HYP-STBS-XAUUSD-M15-009`.
- EA/source: `EA_SupertrendBurstScalperTradeV2`, SHA256 `D950ED04F6940F82354D0D5AF2A2E59C270A71FDFE0A96873C3781849AD959BB`.
- Parent engineering close: HYP011 `PASS_CLOSE_ENGINEERING`; terminal raw-row SHA is bound in the execution authority.
- `InpAuditOnly=false`; all other frozen inputs remain their source defaults and hard-guarded values.

## Sole TRAIN run

- AlphaFactory SHA256: `68BCF4A4F8CF8990A830142F37CDD25C05B665C6BDA02A85DF042BD6DED385E8`.
- FivePercent `XAUUSD`, chart M15.
- Tester preload: `2005.01.01` inclusive through `2023.01.01` exclusive.
- The EA advances indicator state across preload but may enter only inside server-time `[2018.01.01 02:00, 2023.01.01 02:00)`.
- Model 0, execution mode 0, fixed delay 0, current tester spread, USD 10,000, leverage 1:100, control role, telemetry tier off/profile none, non-visual.
- Timeout: 900 seconds. One attempt only under this identity.
- No optimization, alternate timeframe, parameter search, filter, direction removal, session selection, stop/target change or same-ID retry.

A timeout or missing report is an engineering failure, not an economic verdict. A completed report opens exactly one frozen analysis of this baseline.

## Frozen cost treatment

Two evidence layers are deliberately separated:

1. MT5 tester net results include the run's simulated bid/ask spread, commission and swap. The tester PF gate is necessary but not sufficient.
2. Before any economic-valid claim, the closed-trade ledger must be repriced or conservatively stressed with the exact research-only FivePercent XAUUSD cost manifest SHA256 `60302CA3E1BFD0603D5EF38A2EA7B93DE58CA44EEBFE58C6CDA991BD2E184D9B`: complete historical M1 bid/ask coverage for 2018–2022, maximum tester-observed commission USD 4.40 per lot round turn, and the direction-aware 1,000 ms adverse quote proxy whose p90 round trip is 80 XAU pips. x1.5 and x2 multiply the frozen total cost adjustment, not the strategy parameters.

Live deal-history import SHA256 `07CF53E0E45F30F249D92C82E2015D3C9BDB7DADE9C8053091F7663E11B835C4` has zero XAUUSD commission lifecycles and zero observed slippage fills (`MISSING_NOT_ZERO_CANNOT_MINT`). Therefore this baseline can falsify the strategy economically, but even a pass remains research-proxy evidence and cannot by itself authorize OOS, holdout, paper or live deployment. If exact non-double-counted repricing cannot be demonstrated from the run artifacts, the cost verdict is `INCONCLUSIVE`, never a pass.

## Baseline gates

Evaluated only on positions entered in the frozen 2018–2022 TRAIN window:

- at least 500 completed trades;
- 2–5 executed trades per elapsed calendar week;
- LONG and SHORT each at least 30%; no year above 30% of trades;
- positive net expectancy;
- MT5 tester net PF strictly greater than 1.30;
- maximum equity drawdown at most 8%; no negative calendar year;
- repriced/stressed PF x1 greater than 1.30, PF x1.5 at least 1.25 and PF x2 at least 1.00.

Any failed gate parks only this exact mapping. The post-failure review must determine whether the next research loop should test a materially different mechanism; no report-mined rescue is allowed. A complete pass may open a separately frozen higher-fidelity cost/execution stage, then OOS/holdout and robustness in that order.
