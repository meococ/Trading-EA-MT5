# HYP-FRAMA-XAUUSD-M15-001 — source-to-spec receipt

- Native indicator handles: `iFrAMA(XAUUSD,M15,16,0,PRICE_CLOSE)` and `iATR(XAUUSD,M15,14)`.
- Signal calculation reads only shift 2 and shift 1 at the first tick of the next M15 bar; the current forming bar is never an indicator or price input.
- LONG/SHORT predicates exactly match the frozen price/FRAMA crossover. The event is consumed unless decision-to-availability is exactly 900 seconds.
- Stop is the five completed-bar extreme plus/minus `0.20*ATR14`; target is `1.50R`; time exit is 12 completed M15 bars.
- No session, trend, volatility, direction, news or outcome-derived filter is present in the FRAMA execution path.
- Compile evidence: MetaEditor `0 errors, 0 warnings`. Non-repaint evidence: static audit `PASS`.

The inherited trade/lifecycle helpers are used only after a FRAMA event. Legacy KVO calculator code is unreachable from `OnInit`, `OnTick`, and `ProcessFramaClosedBar`; it is not part of this hypothesis decision surface.
