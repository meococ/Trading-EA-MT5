# EA_ProspectiveDOMTape v1.1.0 initialization failure

Date: 2026-08-13

Verdict: `FAIL_ENGINEERING_PRE_SUBSCRIPTION`

- Source compiled through AlphaFactory with `0 errors, 0 warnings`.
- On the live terminal it failed initialization before any DOM subscription.
- Terminal expert log: `EA_ProspectiveDOMTape exclusive JSON open failed` at
  02:34:07; terminal then removed the EA with init code 1.
- `dom_tape_v1_1.jsonl` was exactly zero bytes; CSV and state were not created.
- Cause: v1.1.0 attempted `FileWriteArray` for a BOM on a TXT handle. MQL5's
  array writer is for binary handles, so the fail-closed check rejected startup.
- No snapshot, source value, outcome, order or economic evidence was produced.

Correctness revision v1.1.1 removes the optional BOM write, retains explicit
`CP_UTF8`, and must compile and pass a fresh clean smoke. v1.1.0 has no source
capability authority.
