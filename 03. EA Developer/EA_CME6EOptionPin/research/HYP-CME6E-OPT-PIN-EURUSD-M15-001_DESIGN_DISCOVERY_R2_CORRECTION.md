# HYP-CME6E-OPT-PIN-EURUSD-M15-001 - DESIGN discovery R2 correction

Discovery v1 returned `KILL_SOURCE_DESIGN` solely because its implementation
classified every change in a raw symbol's `expiration` field as unstable
identity.  Source inspection proved this classification wrong before any
statistics payload, futures reference, EURUSD target, or outcome was opened.

Examples such as `3EUJ9 C1055`, `4EUK8 C1015`, `5EUH8 C1015`, and
`WE1N8 C1040` retain the same raw symbol, instrument ID, asset, underlying,
call/put class, and strike while CME sends a later `security_update_action=M`
that revises the expiration timestamp before the event.  These are precisely
the point-in-time definition updates the frozen campaign contract requires the
analyzer to reconstruct.

R2 is an engineering correction, not a strategy rescue:

- identity invariants remain raw symbol, asset, underlying, call/put class, and
  strike;
- instrument-ID remaps are retained for later statistics resolution;
- the latest definition state by `(ts_recv, ts_event)` supplies the expiration;
- expiration revisions are counted and persisted, not treated as identity
  drift;
- a final source-defined expiration that does not match the frozen SER-8206
  nominal clock fails that event and is excluded from the statistics request
  plan, as the original contract stated;
- missing call/put or non-M15 events also fail only that event;
- campaign phase 1 passes only if the remaining non-overlap eligible event count
  stays at least 90 and every DESIGN month still contains eligible Euro FX
  option definitions.

Discovery v1 artifacts remain immutable.  R2 writes new suffixed artifacts and
binds the v1 receipt; no paid request or target/outcome read is authorized by
this correction.

