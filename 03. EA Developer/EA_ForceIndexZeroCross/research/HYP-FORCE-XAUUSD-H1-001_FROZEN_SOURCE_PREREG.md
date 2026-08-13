# HYP-FORCE-XAUUSD-H1-001 — Frozen source preregistration

Frozen: 2026-08-11 before this mechanism's H1 source count.

- Native FivePercent XAUUSD H1, score 2018-01-01 through 2022-12-31.
- `raw_force_t = (close_t - close_(t-1)) * tick_volume_t`.
- `force13` uses EMA alpha `2/(13+1)`, seeded once by the arithmetic mean of
  the first 13 valid raw-force values; invalid input fails closed.
- LONG iff prior completed `force13 <= 0` and current `force13 > 0`.
- SHORT iff prior completed `force13 >= 0` and current `force13 < 0`.
- Equality arms but never emits; decision requires the exact next native H1
  timestamp and source epoch. A gap event is consumed.
- Native-bar-count EMA spans normal market closures. No threshold, signal line,
  session, cooldown, direction deletion, outcome or post-event price.

Source gates: rows >=25,000; feature and exact-next coverage >=99%/97%; events
>=500; pooled cadence 2–5/week; each side >=30%; max-year share <=30%; each
year 1.25–6.5/week. Any fail parks this exact Force13 zero-cross. No MQL5 or
economics is authorized before source PASS.
