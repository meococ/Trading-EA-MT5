# HYP-ST-XAUUSD-H1-001 — Independent Pre-run Review

Status: `PASS`  
Scope: static source-only review; no dataset/analyzer execution.

## Frozen identities

- preregistration SHA256: `DA955208E67D72BB4A584EEEB4AB14D51C36FF813C8E0FD488BCC1EC2EAF8621`
- analyzer SHA256: `2B48F3AA01BB2B00EB66A5AE97346F810EF549CEC2626B0DC9F175EEC890211C`
- tests SHA256: `4D8C9285B642900A95C336B44D0D733CE9059B915B7E5C37B45FD49B33634E68`

## Verdict

No fatal blocker. Source access is correctly bounded from the manifest-declared first native H1 bar through `<2023`, while only 2018–2022 flips are scored. The validator enforces exact inception, sealed upper bound, source order/identity/UTC and full-chain price geometry; the state never resets at 2018 or normal closures.

TR0, subsequent true range, SMA-seeded ATR10 and Wilder recurrence are exact. Index 9 initializes final bands and semantic DOWN state without emitting a flip. Later update order matches the frozen TradingView formula: basic bands, strict final-band carry/update using prior close, strict close/band state transition, then active-line assignment. Equality retains state.

Design-only direction flips, exact next-hour execution, raw-gap consumption, source-only ledger, gates, prehistory authority, exclusive pre-read claim, deterministic replay and receipt/terminal bindings are sound. Manifest metadata binds the expected H1 hash and inception.

No earlier Supertrend object exists. A source pass permits only separately reviewed direct MQL5 formula work; no native handle or unproven `iATR` parity claim. Eleven tests passed. Nonfatal debt: no dedicated equality, lower-band strict-branch or design-boundary continuity unit test.

Authorize exactly one source/cadence attempt after a matching registry row with explicit prehistory permission. No MQL5, outcomes, economics, validation, holdout, paper or live authority is granted.
