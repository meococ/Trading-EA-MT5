# HYP-APC-XAUUSD-M15-001 — independent pre-run review

Verdict: `PASS_BASELINE`

Scope: read-only review of the exact frozen source and build package before any APC MT5 outcome was opened.

- Source SHA256 `ED33D6D4E41144BA423D3039C9C12FB6166A0B6C2583918F0B8655971B5FECF6` matches the compiled and audited object.
- Seven source-to-spec tests pass.
- AlphaFactory compile log SHA256 `883096C856DFD387FED6D973E260F006FF07C1F44ED2FB24CF9C8E3A3BFA828E` reports exactly `0 errors, 0 warnings`; EX5 SHA256 is `F480E5EE38B13144F493FD8D3B212B443A45E2E11D3151ECB6C4CD0081BB0C6E`.
- Official non-repaint audit SHA256 `D26BEB73F271AFD38F365E08703AB2D38232852727BB502B676B14FA303FC197` is PASS with zero findings and binds the exact source.
- `CopyRates` begins at shift 1; release/pullback/impulse are completed bars `t/t-1/t-2`. ATR, EMA, ADX and DI shifts match the preregistration.
- LONG/SHORT predicates, structural stop, 1.45R target and release-extension logic are symmetric and materially distinct from Donchian breakout and multi-bar pivot reclaim.
- Closed-data, indicator, true-range, scheduling-clock and attempted non-`DONE` send failures latch `runtime_failed`; later entries are blocked.
- FOK/full-DONE entry, `OrderCheck`, risk sizing, free-margin gate, inventory gate, time exit, Friday/weekend/design-end flatten and close-failure handling are adequate for one bounded baseline.

Authorization is limited to exactly one untuned XAUUSD M15 Model-0 TRAIN baseline. This review makes no economic, validation, holdout, promotion or live claim.

