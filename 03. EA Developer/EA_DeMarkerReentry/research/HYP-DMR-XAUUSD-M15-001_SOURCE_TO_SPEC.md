# HYP-DMR-XAUUSD-M15-001 — source-to-spec receipt

- Native `iDeMarker(...,14)` buffer shift2/shift1 implements the frozen completed-bar exits from 0.30/0.70 extreme zones.
- Native ATR14 shift1 and five completed rates shift5..shift1 implement the frozen stop; target remains `1.50R` and time exit remains 12 bars.
- A signal is executable only when the next native M15 open is exactly 900 seconds after its decision bar; a gap consumes the event.
- Native indicator readiness is deferred, but the first ready tick re-anchors the scheduler and returns before signal processing. A never-ready run is marked `runtime_failed=true` at deinit.
- Stopout-aware downward sizing, one-position/no-pending inventory, daily/peak risk locks, Friday/weekend/design-end handling and API fail-closed behavior are inherited unchanged from the reviewed CCI/FRAMA lifecycle skeleton.
- Legacy KVO helpers remain unreachable debt: `OnTick` calls only `ProcessDeMarkerClosedBar`.

This receipt authorizes one untuned Model-0 TRAIN baseline only. It does not authorize optimization, validation, holdout or promotion.
