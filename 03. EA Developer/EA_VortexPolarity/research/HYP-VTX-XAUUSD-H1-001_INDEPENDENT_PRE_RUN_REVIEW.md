# HYP-VTX-XAUUSD-H1-001 — Independent Pre-run Review

Status: `PASS`  
Scope: static source-only review; no source dataset/analyzer execution.

## Frozen identities

- preregistration SHA256: `A21B969D644CC935552ED4AF5C8DD1D1EDAF14F97BD518C532F944CBBB957B78`
- analyzer SHA256: `EABF3C90858CC0470B3CAF6C1355963D5F9005B5EA306CC45D220D693FEE77C0`
- tests SHA256: `96E48561EE1518CDFED14DC995089A8E15ABE134753601D22610B7390D526DFF`

## Verdict

No fatal blocker. The analyzer implements standard unscaled Vortex-14 exactly: true range, VM+/VM-, rolling sums and normalization. Current and prior VI validity produces dependency `t-15..t` and first crossover row 15. Prior equality may arm; current polarity is strict. Decision is exact next hour, and raw gap events are counted then rejected using only the next timestamp.

The ledger is restricted to the source-only allowlist. Native XAUUSD H1 schema/window/order/UTC/geometry validation, the manifest-bound H1 hash, sealed PyArrow read/postcheck, durable exclusive pre-read claim, same-frame byte replay, and receipt/terminal bindings are sound. Gates match the preregistration.

No previous Vortex family exists in registry/failure canon. The mechanism is materially distinct from Ichimoku. A source pass can authorize only a separately reviewed direct MQL5 formula implementation; MT5 has no official native `iVortex` handle and no such claim is permitted.

Eleven tests passed. Nonfatal debt: no dedicated prior-equality or zero-TR case, though the implementation is unambiguous.

Authorize exactly one source/cadence attempt after a matching registry row. No MQL5, outcomes, economics, validation, holdout, paper or live authority is granted.
