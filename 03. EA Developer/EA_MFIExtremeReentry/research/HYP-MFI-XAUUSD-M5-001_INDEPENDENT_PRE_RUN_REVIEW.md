# HYP-MFI-XAUUSD-M5-001 — Independent Pre-run Review

Date: 2026-08-09  
Reviewer: read-only sub-agent `t2_campaign_audit`  
Verdict: `PASS`

The reviewer did not open the dataset, run the analyzer or edit files.

## Frozen identities

- Preregistration SHA256: `F89BE96DE95E484A7734F89FC565F3113521C41215F40CCAEC66A0D326D57295`
- Analyzer SHA256: `FEEB94E517FB9D8ACE560703F98BE4F28150AA0A2071D01A179C365966DFDC2E`
- Tests SHA256: `1153BBC3FB429DE6EBFBC52E927A40FEF5BB36C1FE61B4DCEEC0C86BA5ED951E`
- Main-agent tests: `10 passed`

## Findings

- The MFI14 formula matches TradingView: typical price, raw flow, fourteen positive/negative flows classified by typical-price change, ratio, and conventional 20/80 levels.
- MFI at bar `i` uses raw bars `i-14..i`; an event at `t` uses `MFI(t-1)` and `MFI(t)`, so the exact union is `t-15..t`. Coverage begins correctly at index 15, the sixteenth row.
- Equal typical price contributes zero to both sides. Positive-only produces MFI 100, negative-only produces zero, and both-zero is invalid/fail-closed.
- Crossings are completed-bar causal. The only forward reference is the next row's timestamp; no next price is accessed.
- Exact all-valid masks, predicate-filtered sealed-window read, ledger schema guard, cadence/year arithmetic, registry/self-hash authority, exclusive durable attempt claim, terminal receipt and byte replay are sound.
- A later native `iMFI(..., VOLUME_TICK)` parity implementation is compatible with the MQL5 interface, but is not yet authorized.
- Repository de-duplication passes: no prior MFI object was found, and the mapping is distinct from TVER, TFCVD, VCEX, ECRS, ASRS, ARUC and LVOR.

Nonfatal debt: the tests do not isolate the MFI 100, 0 and both-zero branches into separate unit cases, although the frozen implementation is unambiguous and the static review found no execution blocker.

Recommendation: authorize exactly one source-only attempt, conditional on the latest registry row binding the identities above. No economics, MT5/MQL5 build, validation, holdout or live authority.

