# V7 H4/D1 Local De-Dup Baseline — 2026-07-13

Status: `PRE_RESULT_BASELINE / READ_ONLY / NO_BUILD_AUTHORITY`

## Purpose

This memo freezes the local family boundary before the Deep Research V7 result
is read. It prevents a later proposal from gaining novelty merely through a
slower timeframe, a renamed indicator, or selective citation of an older run.

It does not inspect V7 outcomes, create a new hypothesis, authorize an offline
probe, or authorize EA source/compile/backtest work.

## Binding

- V7 packet:
  `03. EA Developer/EA_SonicR/research/20260713_NEW_STRATEGY_DEEP_RESEARCH_SCOPE_EXPANSION_V7.md`
- V7 conversation:
  `https://chatgpt.com/c/6a55088f-89b4-83ec-97b2-54a3a185ccb5`
- Canonical local evidence:
  `02. AlphaFactory/STRATEGY_LOG.md` and
  `03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl`.

## Frozen near-duplicate map

| Family | Local evidence | Binding lesson for V7 |
|---|---|---|
| H4 moving-average/ribbon pullback trend | `S693 / EA_H4Ribbon`, USDJPY H4, 108 trades, PF `0.87`, DD `11.6%` | Any EMA/ribbon/channel/trend-pullback answer needs a different causal variable, not different periods or normalization. |
| Daily compression / inside-day breakout | `S694`, XAUUSD D1, 20 trades, PF `0.83`; `S695`, USDJPY D1, one trade | Slowing an inside-bar/compression breakout to D1 fails cadence/evidence and is closed as a generic pattern family. |
| H1 inside-bar compression | `S232`, USDJPY H1, 100 trades, PF `1.65`; `S235`, GBPUSD H1, 66 trades, PF `1.31`; `S237`, USDJPY H4, only 6 trades | Older high-PF H1 results are far below the 2–5/week North-Star cadence. Day/session-filter descendants are not a new H4/D1 mechanism. |
| Autocorrelation regime switch | `S548 / EA_ACF`, XAUUSD M15, 1,430 trades, PF `0.88`, DD `100%` | ACF/Hurst/entropy or momentum-versus-reversion switching must not be restated as a medium-horizon behavioral mechanism without an independent observable. |
| Choppiness/volatility-gated trend | `S628`, XAUUSD PF `0.95`; `S629`, USDJPY PF `1.12`; filtered descendants relied on weekday/session selection | Choppiness, ATR, realized-volatility, or regime filters applied to generic trend are not independent novelty. |
| Multi-pair consensus / common-currency direction | `S618 / EA_MultiJPY`, 2,334 trades, PF `1.02`; existing `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` remains `IDEA / COST-DATA BLOCKED` | V7 may not rename consensus, common-USD factor, strongest-pair routing, or pair ranking at H4/D1. |
| Predictive lead-lag / laggard catch-up | Frozen controls in `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`; `S619` cross-asset catch-up PF `0.86`; `S670` divergence PF `0.95` | Cross-pair ranking is legal only if the new mechanism is not prediction by leader/laggard ordering or convergence. |
| Low-frequency cross-market/basis convergence | `S621 / EA_COMEXRevert`, 686 trades, PF `1.04` | A slower convergence wrapper cannot substitute for executable venue/basis data. |
| Cross-day same-interval momentum | `S689`, 15 trades, PF `0.22`; `S690`, 4 trades, with weekend/bar-shift implementation defect | Calendar-aligned interval momentum is both locally weak and implementation-contaminated; it cannot be a V7 candidate without a different thesis and clean indexing proof. |
| H1 open-range breakout | `S678` fresh hardening rerun, PF `1.14`, 593 trades, with remaining calendar/correlation blockers; `S691` XAUUSD PF `0.95` | A wider bar or different session does not create novelty; any open-range candidate is closed unless it proves a separate causal state. |
| Retail tick-volume/flow acceleration | `S677` PF `1.17`; `S679` PF `1.25` plus 2019 PF `0.65`; V5 causal audit | Tick volume cannot be presented as institutional flow and remains outside V7's medium-horizon legal mechanisms. |

## Coordinator intake rule

When V7 completes, a proposal passes local de-dup only if all are true:

1. its causal variable is observable from the V7 allowed surface without
   replacing institutional data with a price/tick-volume transform;
2. it is not any row in the frozen map under a new timeframe, indicator,
   threshold, pair rank, or portfolio wrapper;
3. its source sampling horizon is compatible with H4/D1 decisions;
4. its structural cadence can reach 2–5 pooled trades per elapsed week before
   parameter search;
5. its negative control isolates the claimed mechanism from ordinary return,
   trend, volatility, calendar, or pair-ranking effects.

Failure of any condition is `KILL_AT_INTAKE_DUPLICATE_OR_CAUSAL_MISMATCH`.

## Authority boundary

Until V7 completes and a coordinator audit passes all five intake rules:

- no candidate-registry append;
- no preregistration;
- no analyzer/probe implementation;
- no MQL5 source or include change;
- no MetaEditor compile or Strategy Tester run.
