# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-005 — source continuation preregistration

Status: `REVOKED_UNAUTHORIZED_PAID_CONTINUATION`.

This continuation did not have current Owner approval for paid data. A competing
process nevertheless completed the 63 paid source requests. Those artifacts are
preserved only as quarantined incident evidence. They may not be retried, used for
source acceptance, joined to outcomes, used for economics, or promoted into an EA.
The executable entry point is fail-closed.

## Scope

Continue the interrupted DESIGN source census without retrying anything. The parent
atomic manifest binds exactly:

- 256 `COMPLETE` events, of which 255 passed semantics;
- 8 `IN_FLIGHT` payment/source-ambiguous events, frozen forever as
  `SOURCE_AMBIGUOUS/FLAT`;
- 63 `UNATTEMPTED` events (`EVT0267` through `EVT0329`), and only these may be acquired;
- the original two zero-byte quote events remain `SOURCE_UNAVAILABLE/FLAT`.

The 63 frozen live estimates sum to USD 0.434695020317. Before purchase, re-quote only
those 63 windows and abort unless every event is positive and at most USD 0.03 and the
aggregate is at most USD 0.50. Make exactly one `timeseries.get_range` per window, no
retry, batch, subscription, or access to any earlier ambiguous partial.

## Formula and gates

Use the unchanged parent depth formula and per-event integrity gates. Combine the 256
parent COMPLETE receipts with the 63 child results and freeze all other identities as
described above. Require:

- 63/63 child requests complete with zero child failures;
- all 329 DESIGN clock identities accounted;
- exactly eight ambiguous and two unavailable identities, all FLAT;
- semantic pass share at least 95% among the 319 completed source events;
- at least 209 non-FLAT classifications;
- continuation and reversal each at least 10% of semantic-pass events;
- long and short each at least 20%; maximum class share at most 80%.

This is source/cadence only. No outcomes, returns, PnL, economics, MQL5, MT5,
validation, holdout, optimization, paper, promotion, or live authority is granted.
