# HYP-MFI-XAUUSD-M5-002 — Independent Pre-run Review

Date: 2026-08-09  
Reviewer: read-only sub-agent `t2_campaign_audit`  
Verdict: `PASS`

No dataset/analyzer execution or file edit was performed by the reviewer.

## Frozen identities

- Preregistration `AF4E4732BF9E7377881A62BF3DFAC528915DD7FA15BCC6E4506371EC5C069B06`
- Analyzer `23602E8FC39B53F2230C97416F622C91FED1612CB9B98120C33325998DE28052`
- Tests `6EA05831B7D967304598F8F8B3B7DB4389D86727BF9CFCC5AA57033FB1B803F1`
- Bound MFI001 calculation dependency `FEEB94E517FB9D8ACE560703F98BE4F28150AA0A2071D01A179C365966DFDC2E`
- Main-agent tests: `10 passed`

## Findings

The FSM is the exact causal bullish/bearish inverse frozen in the preregistration: inclusive 20/80 arm/restart, strict ADVANCE extrema, strict prior-bar pullback, strict frozen-trigger break. Invalid MFI resets both machines. Any raw event or conflict resets both machines. A gap event is consumed while only the next timestamp is accessed.

Feature coverage excludes exactly the first fourteen unavailable MFI rows. Executable/raw-event coverage, elapsed-calendar-week cadence and per-calendar-year arithmetic match the contract. Predicate-filtered sealed access and post-filter validation are inherited from the exact hash-bound MFI001 calculation dependency. The event ledger contains no price/outcome field. Deterministic replay and exclusive durable one-shot claiming are present.

The only operational prerequisite is a canonical source-only registry authority row binding the identities above. Nonfatal test debt: simultaneous conflict and bearish gap/equality symmetry are not isolated in direct unit tests; static inspection found no implementation blocker.

Recommendation: authorize exactly one source-only attempt. Economics, MT5/MQL5 build, validation, holdout and live remain false.

