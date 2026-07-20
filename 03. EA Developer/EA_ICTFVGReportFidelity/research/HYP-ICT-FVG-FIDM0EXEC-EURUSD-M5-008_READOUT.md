# HYP-ICT-FVG-FIDM0EXEC-EURUSD-M5-008 - corrected-execution Model-0 readout

Verdict: **KILL_AT_MODEL0_CORRECTED_EXECUTION_CONTROL_LOSS_CHALLENGER_ZERO_TRADE**  
Promotion eligible: **false**  
Holdout 2023+: **sealed / not loaded**

## Why the parent result required correction

The parent control `20260719_005603` was invalid. Its source rejected a
successful `OrderCheck()` basic check unless `MqlTradeCheckResult.retcode` was
`TRADE_RETCODE_DONE` or `TRADE_RETCODE_PLACED`. The Tester journal proved
11,330 false rejections with retcode zero and five separate genuine invalid-stop
rejections. This made the earlier zero-trade control and its “risk/geometry”
interpretation false.

HYP-008 was frozen after diagnosis and before the child source or outcome. The
legal delta accepts boolean-success `OrderCheck` results with retcode zero and
adds mutually attributable rejection counters. Every input line and both
preset files remain byte-identical to the parent. No strategy threshold,
session, news, stop, target, risk rule or holdout changed.

Engineering proof: red-first contract 4/4 failed on the parent behavior; final
package tests 26/26 PASS; AlphaFactory compile 0 errors / 0 warnings;
exact-source non-repaint V11 PASS with zero findings. Canonical source SHA-256
is `7F5AD64F2C622B0426BA475B855257AAB560026C2882C1D45D7C6826DAF33EAE`.

## Corrected Model-0 pair

Both runs used FivePercent EURUSD M5, MT5 Model 0, 2019.01.01-2022.12.31,
deposit 100,000, 100% history quality, 298,483 bars and 79,486,116 ticks.

### High-recall control - run `20260719_125520`

The execution correction is proven operational:

- 12,340 sweep opportunities.
- 122 successful retcode-zero OrderChecks, 122 send attempts and 122 opened
  lifecycles; zero OrderCheck, stop, volume or send rejection.
- 698 news rejections, 283 session-boundary rejections, 45 exposure rejections.
- 11,192 prop rejections after the persistent drawdown gate stopped trading.

Tester metrics before verified cost repricing: 122 trades, cadence 0.5849/week,
net -$7,944.29, PF 0.5774, win rate 41.80%, expectancy -$65.12/trade and max DD
7.697%. All trades occurred in January-March 2019; the account-DD gate then
left 45 months inactive. The lifecycle sidecar contains 244 deal rows plus its
header, consistent with 122 completed positions.

`validate-full` returned `REVIEW`, passing only 4/14 numeric/artifact gates.
Cadence failed, cost-adjusted PF stayed blocked by missing verified execution
provenance, robustness passed 0/7 diagnostics, fixed-parameter WFA had 2/5
profitable OOS slices, Monte Carlo P95 DD was 9.8% versus the 8% ceiling and the
equity audit was `WARN`. These secondary diagnostics cannot rescue a control
whose gross Tester PF is already far below one.

### Full report-fidelity challenger - run `20260719_125626`

The new counters fully reconcile the zero-trade funnel:

| Stage | Count | Terminal accounting |
|---|---:|---|
| Sweep/reclaim | 12,340 | 12,047 displacement timeouts + 293 qualified displacement/FVG/OB overlaps |
| Qualified displacement/FVG/OB overlap | 293 | 144 pre-MSS mitigations + 149 M15 MSS |
| Closed-M15 MSS | 149 | 3 day expiry + 107 retest timeout + 1 stop breach + 38 first touches |
| First overlap touch | 38 | 32 depth rejects + 5 rejection-candle rejects + 1 valid retest |
| Valid first retest | 1 | 1 ADX-threshold reject; 0 ADX pass |
| Entry/trade | 0 | `TryOpenTrade` was never called |

The challenger therefore remains zero-trade for signal reasons, independently
of the repaired OrderCheck path. PF, WR, expectancy and economic drawdown are
undefined for this empty trade set.

## Decision

- The corrected high-recall sweep control is economically inferior: too few
  trades over the full window, PF below one before verified cost repricing and
  rapid exhaustion of the 8% account-DD budget.
- The full report-fidelity chain is structurally over-constrained for this
  frozen EURUSD M5 implementation: 97.63% of sweeps fail to produce the ordered
  displacement/FVG/OB event, and only one of 149 MSS events survives the first
  retest contract before ADX.
- The paired system is terminal. Do not relax the six-bar displacement window,
  first-touch depth/rejection, ADX, session, stop/risk or prop gates using this
  outcome. Any different design is a new strategy object and requires a fresh
  preregistration and untouched evaluation window.

Historical same-broker spread, commission and direction-aware slippage
provenance remains insufficient. No optimization, additional rerun, WFA-based
tuning, 2023+ access, promotion, paper or live attachment is authorized. This
falsifies the exact quantified object; it does not prove all discretionary
ICT/FVG or contextual OHLC trading lacks edge.
