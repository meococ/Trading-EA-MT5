# HYP-ICH-XAUUSD-M5-001 — Independent Pre-run Review

Status: `PASS`  
Scope: static, outcome-blind package review only; no dataset/analyzer execution.

## Frozen identities

- preregistration SHA256: `3811EDC4E5141A07D4074F2613A62540EA320BFB1D67A64BF69971AD600099A8`
- analyzer SHA256: `F9BAF1626EF05A623C49B16B817D405AE1C9689845E5E5E8F8E5E23F937C8114`
- tests SHA256: `2689F7C26B92AF3F88EFC9C4C857534907380D97501B869A21D70EE370D18B58`

## Verdict

No fatal blocker. Trailing 9/26 midranges, raw Span A, trailing 52 Span B and the 26-bar displayed-cloud shift are exact. The complete dependency is `t-77..t`; all 78 source rows are finite/geometrically gated, the first usable row is 77 and coverage divides by `len-77`.

Prior equality can arm the Tenkan/Kijun cross, while the current cross, cloud clearance and cloud ordering are strict. Raw events at a missing next timestamp are consumed; only the next timestamp is inspected. Bar-count lookbacks intentionally span normal market closures as preregistered. The ledger contains only frozen signal-bar source fields, timestamps and direction.

The sealed PyArrow design-window predicate/postcheck, selected-frame checks, exclusive pre-read marker, deterministic replay and complete receipts are sound. Repository de-dup found no earlier Ichimoku object. Native `iIchimoku` parity is feasible through buffers 0/1/2/3, but shifted Senkou buffer indexing must be frozen and tested against the offline displayed-cloud formula during build if source gates pass.

Eleven focused tests passed. Nonfatal debt: direct equality-boundary coverage and native-buffer parity are absent; the latter is deliberately deferred to a source-authorized build stage.

Authorize exactly one source/cadence attempt only after a matching registry probe row. No outcomes, economics, MT5, MQL5, validation, holdout, paper or live authority is granted by this review.
