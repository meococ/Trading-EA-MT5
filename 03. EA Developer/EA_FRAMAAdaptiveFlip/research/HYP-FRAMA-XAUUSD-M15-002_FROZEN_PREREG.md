# HYP-FRAMA-XAUUSD-M15-002 — Frozen native-warmup engineering revision

Status: `FROZEN_BEFORE_REVISION_SOURCE_AND_OUTCOMES`.

Parent HYP001 stopped in `OnInit` before processing one bar because native FRAMA/ATR buffers were transiently not calculated. No outcome or economic metric was opened.

HYP002 preserves the exact HYP001 XAUUSD M15 FRAMA16 price-crossover thesis, 2018–2022 TRAIN window, risk 0.25%, five-bar plus `0.20*ATR14` stop, `1.50R` target, 12-bar exit, daily/account locks, margin protection, cadence and PF gates. It changes only:

- fresh ID `HYP-FRAMA-XAUUSD-M15-002`, magic `5604102`, variant `FRAMA16_PRICE_CROSS_ADAPTIVE_FLIP_DEFERRED_WARMUP`;
- `OnInit` validates the native handles but allows calculated buffers to become ready on later ticks;
- no signal processing occurs before both FRAMA and ATR buffers pass the frozen readiness sample;
- if readiness never succeeds, `OnDeinit` must report `runtime_failed=true` so zero activity cannot become an economic result.

No signal, stop, target, sizing, filter, session, direction or outcome-derived change is authorized. Exactly one untuned Model-0 baseline is allowed after compile/tests/non-repaint review pass.
