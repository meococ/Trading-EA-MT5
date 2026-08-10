# HYP-FRAMA-XAUUSD-M15-002 — source-to-spec receipt

- Signal, FRAMA16/ATR14 shifts, five-bar stop, 1.50R target, 12-bar exit, risk and margin logic are unchanged from HYP001.
- Fresh identity only: HYP002, magic 5604102, deferred-warmup variant.
- `OnInit` validates both native handles. `OnTick` attempts the frozen readiness sample and returns before signal processing until it passes.
- `OnDeinit` forces `runtime_failed=true` if readiness never passed; zero activity cannot be accepted as economic evidence.
- The parent failure processed zero bars and opened no outcome metric.
