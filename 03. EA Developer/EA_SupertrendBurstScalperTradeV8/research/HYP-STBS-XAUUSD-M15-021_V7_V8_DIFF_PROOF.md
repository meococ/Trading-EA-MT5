# HYP-STBS-XAUUSD-M15-021 — V7 to V8 bounded diff proof

## Identities

- Parent V7 source SHA-256: `B49D1CA7868B723C10B12A23D2C07CA1DF5F2A0BB86B0860C05FD34CE0F03750`
- Child V8 source SHA-256: `11E44FF9B51DA50F6DF25C54858BFF492C89A58EED04684C828A70740B37FED9`
- V8 EX5 SHA-256: `E98A3535D4E14081C42E88101A32FB251FC11BA78DE79DEA0C444479AC4FC31B`
- V8 compile log SHA-256: `C36878CF9950E743A97394E21DD083CD75EFCDD2DFB2F06CAA20DA0208779A20`
- Compile result: `0 errors, 0 warnings`

## Authorized changes only

1. Fresh identity: version 8.00, HYP021, V8 variant, EA name and magic `5604121`.
2. Stable lifecycle transport:
   - trade callbacks enqueue the exact deal ticket idempotently instead of reading a newly added deal synchronously;
   - a ticket is acknowledged only after that ticket is logged or proven irrelevant, never merely because a history scan returned success;
   - transient replay failure is retried for up to the existing 60-second visibility bound;
   - OnInit performs a full restart replay before signals and OnDeinit fails closed on unresolved tickets;
   - deal fields are captured before any ownership/history reselection;
   - ownership and cumulative volume are recomputed from full history using exact `DEAL_POSITION_ID`;
   - replay is ordered by `(DEAL_TIME_MSC, ticket)` and processes OPEN before CLOSE;
   - every terminal logging rejection emits a stage-coded `STBS_LIFECYCLE_REJECT`.
3. Bounded journal serialization:
   - safe actual-margin evidence is counted once per position; only unsafe transitions are printed;
   - redundant normal-path queue, entry-request, margin-check and successful request-result rows are suppressed;
   - lifecycle CSV and RunMeta remain authoritative;
   - trade mode emits no per-event `STBS_SIGNAL` or final-deal journal rows; summary counters and lifecycle rows carry the evidence;
   - the frozen one-MiB AlphaFactory journal cap is preserved and any truncation remains an engineering failure.

## Frozen economic behavior

Focused tests compare the V7 and V8 bodies of the Supertrend recurrence, entry geometry and downward-only volume search exactly. They also bind the unchanged flip, exact-next, M15 ATR14, geometry, account-safe margin formulas and the same three OrderSend gateways.

There is no change to:

- H1 Supertrend 10x3 flip signal;
- closed-bar or DESIGN-window mapping;
- M15 ATR14;
- risk 0.25%, stop 1.0 ATR, target 1.5R or eight-bar hold;
- Friday entry/flatten rules;
- 5% new-margin ceiling or account stop-out headroom;
- spread, commission, slippage proxy or any economic gate;
- direction, session, debounce, cooldown, optimization or outcome filter.

## Verification

- Focused tests: `10 passed`
- Test SHA-256: `A0A019EE936CC9C881816E0A65C9A2D681EBCCB5E4FD2F8791D5474F00A58509`
- Non-repaint manifest SHA-256: `E95C3B3C2D8D47E396218F37F9A64A0529C5E775C6AC59C73EFCAD77FC26DA0E`
- Non-repaint audit SHA-256: `2E1D8FEE3444540792014D124DA40A0264CC744F45EC377BCC4970E88D838012`
- Non-repaint verdict: `PASS`
- Research cost manifest SHA-256: `0FBFDE0F0BCC4E6F829EAA7812D530AF99106E5641444DF3DD2A390353A06215`

HYP021 is an engineering revision prompted by an inadmissible runtime/evidence failure. It is not a PF-driven strategy rescue.
