# HYP-STBS-XAUUSD-M15-021 — Independent pre-run review

## Verdict

`PASS_PRE_INITIAL_AUTHORITY`

No fatal blocker remains in the reviewed V8 source package. This verdict authorizes only the initial screened registry row and deterministic task-packet construction. It does not authorize MT5 execution until a successor screened row binds the exact packet and builder evidence.

## Reviewed identities

- Source SHA-256: `11E44FF9B51DA50F6DF25C54858BFF492C89A58EED04684C828A70740B37FED9`
- EX5 SHA-256: `E98A3535D4E14081C42E88101A32FB251FC11BA78DE79DEA0C444479AC4FC31B`
- Compile log SHA-256: `C36878CF9950E743A97394E21DD083CD75EFCDD2DFB2F06CAA20DA0208779A20` (`0 errors, 0 warnings`)
- Preregistration SHA-256: `ADE0D4831D0C97C4A3E50BB00C0760E00E03B1C5AFE0626BDEA29D03553EE9C9`
- Bounded diff proof SHA-256: `CDDA40FD7B493BFE77C3290E10007E4AF8ED5628C613F8C8C8D8B1C45DB6274D`
- Focused test SHA-256: `A0A019EE936CC9C881816E0A65C9A2D681EBCCB5E4FD2F8791D5474F00A58509` (`10 passed`)
- Non-repaint manifest SHA-256: `E95C3B3C2D8D47E396218F37F9A64A0529C5E775C6AC59C73EFCAD77FC26DA0E`
- Non-repaint audit SHA-256: `2E1D8FEE3444540792014D124DA40A0264CC744F45EC377BCC4970E88D838012` (`PASS`)
- Packet-builder pre-row SHA-256: `929EDF3D81DF5DCD56C5312026A0E8B847AE2357B0589DC512597C0772F1F7AE`

## Findings

- `OnTradeTransaction` enqueues the exact deal ticket idempotently and never treats a generic successful history scan as acknowledgment.
- A queued ticket is removed only after that ticket is logged or proved irrelevant. Missing/unstable ownership remains unresolved and reaches the frozen timeout/fatal path.
- Initialization performs full lifecycle replay before signal processing; deinitialization fails closed if any ticket remains unresolved.
- Replay remains sorted by `(DEAL_TIME_MSC, ticket)`, processes OPEN before CLOSE, and preserves cumulative partial-close finality.
- Trade mode suppresses per-event `STBS_SIGNAL` and safe per-tick margin journal spam. The frozen `1,048,576` raw-byte cap and `truncated=false` requirement remain fail-closed engineering gates.
- V7 to V8 does not change the Supertrend signal, M15 ATR, entry geometry, account-safe volume selection, exits, risk, costs, or economic thresholds.

## Authority sequence

1. Append one initial HYP021 screened row with MT5 execution still closed and task-packet construction authorized.
2. Replace the builder's pending authority-row placeholder with the exact compact raw-row SHA-256.
3. Build the deterministic packet without opening MT5 or outcomes.
4. Append a successor screened row binding the exact builder, packet, registry, prereg, source, compile, non-repaint, cost and review hashes.
5. Only that successor row may authorize the sole `STBS021-MODEL0-TRAIN-001` execution.

Any journal truncation, lifecycle mismatch, runtime fatal, orphan exposure, forced stop-out, or evidence mismatch consumes the sole attempt and yields no economic verdict.
