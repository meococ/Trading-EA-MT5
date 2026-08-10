# HYP-CCI-XAUUSD-M15-001 — source-to-spec receipt

- Native `iCCI(...,20,PRICE_TYPICAL)` buffer shift2/shift1 implements the frozen prior/current CCI cross through `+100/-100` on completed M15 bars.
- Native ATR14 shift1 and five completed rates shift5..shift1 implement the frozen stop; target remains `1.50R` and time exit remains 12 bars.
- A signal is executable only when the next native M15 open is exactly 900 seconds after its decision bar; a gap consumes the event.
- Native indicator readiness is deferred, but the first ready tick re-anchors the scheduler and returns before any signal processing. A never-ready run is marked `runtime_failed=true` at deinit.
- Stopout-aware downward sizing, one-position/no-pending inventory, daily/peak risk locks, Friday/weekend/design-end handling and API fail-closed behavior are inherited unchanged from the reviewed FRAMA skeleton.
- Legacy KVO helpers remain unreachable debt: `OnTick` calls only `ProcessCciClosedBar`; no KVO preload, state advance or signal function is reachable from the active path.

This receipt authorizes one untuned Model-0 TRAIN baseline only. It does not authorize optimization, validation, holdout or promotion.
