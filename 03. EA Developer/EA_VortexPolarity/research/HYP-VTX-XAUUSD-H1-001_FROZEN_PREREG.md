# HYP-VTX-XAUUSD-H1-001 — Frozen Vortex-14 Polarity-crossover Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`  
Informing evidence: terminal source-only Ichimoku H1 insufficiency; no economic result.

## Identity and thesis

- Hypothesis: `HYP-VTX-XAUUSD-H1-001`
- Family: `vortex-14-unscaled-directional-range-polarity-crossover`
- Symbol/timeframe: FivePercent XAUUSD native H1 Bid bars
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole attempt: `VTX001-SOURCE-ATTEMPT-001`

TradingView documents Vortex as two directional trend lines whose crossovers identify trend reversals/direction. Unlike Ichimoku midrange/cloud alignment, Vortex measures interbar high/low directional movement normalized by true range. Repository de-dup found no Vortex/VI/VM family object.

MT5 has no official built-in `iVortex`. A source pass would therefore authorize only a direct reviewed MQL5 formula implementation and offline/MT5 parity harness, never a native-handle parity claim.

## Exact causal formula

Period is exactly 14. Values are frozen as unscaled ratios, not multiplied by 100.

For bar `i`:

- `TR[i] = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))`
- `VM+[i] = abs(high[i]-low[i-1])`
- `VM-[i] = abs(low[i]-high[i-1])`
- `VI+[t] = sum(VM+[t-13..t]) / sum(TR[t-13..t])`
- `VI-[t] = sum(VM-[t-13..t]) / sum(TR[t-13..t])`

Current VI at `t` depends on bars `t-14..t`; prior VI at `t-1` depends on `t-15..t-1`. The crossover union is exactly `t-15..t`, so first usable row is index 15. All 16 bars must have finite/geometrically valid high, low and close; both current and prior TR sums must be finite and strictly positive. Bar-count windows span normal market closures.

## Signal and execution mapping

- raw LONG at completed bar `t`: prior `VI+ <= VI-` and current `VI+ > VI-`.
- raw SHORT: prior `VI+ >= VI-` and current `VI+ < VI-`.
- Prior equality can arm; current equality is no event.
- An executable event requires the immediately following native H1 timestamp to equal `t+1 hour`. A raw gap event is consumed and not persisted. Only the next timestamp is inspected; no next price is read.
- Decision timestamp is `t+1 hour`.

Forbidden: threshold/separation filter, smoothing, alternative periods, persistence/debounce/cooldown, session/news/price/volume/ATR/ADX/Ichimoku filters, position state, optimization and outcomes.

## Frozen source and gates

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- native H1 data SHA256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`
- only symbol/timeframe/source epoch/time/UTC ambiguity/high/low/close may be read;
- PyArrow materializes only 2018–2022, followed by a fail-closed post-read assertion.

All gates must pass:

1. hash/registry/one-shot bindings and byte-identical replay;
2. at least 25,000 design rows;
3. feature coverage at least 99.0% after exactly 15 warmup rows;
4. exact-next H1 coverage at least 97.0% of raw crosses;
5. at least 500 executable events;
6. pooled cadence 2.0–5.0/week;
7. each direction at least 30%;
8. no year above 30%;
9. each year cadence 1.25–6.50/week;
10. zero conflicts;
11. exact source-only ledger allowlist.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_VORTEX14_POLARITY`. All pass gives `SCREENED_SOURCE_PASS_MQL5_DIRECT_VORTEX_BUILD_AUTHORIZED`, allowing only formula implementation/parity/correctness work. Economics remains unauthorized.

## Authority boundary

No source access until analyzer/tests/hashes receive independent review and registry authority. No MQL5, MT5 tester, economics, validation, holdout, paper, promotion or live authority is granted here.
