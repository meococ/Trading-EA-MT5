# HYP-QPF-EURUSD-M1-002 engineering closeout

Verdict: `ENGINEERING_INVALID_CACHED_INPUT_NO_SOURCE_ATTEMPT`

The single authorized launch compiled cleanly, but MT5 initialized the EA with the cached value `InpHypothesisId=HYP-QPF-EURUSD-M1-001`. The frozen HYP002 source correctly failed closed before `OnTick` because the exact identity contract was not satisfied.

Evidence:

- Run: `EA_QuotePathFidelityProbe/20260812_202440`
- `config.ini` contains an empty `[TesterInputs]` section.
- `run_manifest.json` records `overrides=""` and no captured sidecar.
- Tester journal records the cached HYP001 value, `QPF_IDENTITY_FAIL`, `emitted_buckets=0`, and `orders_sent=0`.
- No tick payload, outcome price, trade result, or economics was read or evaluated.

Governance:

- HYP002 is terminal and must not be rerun under the same identity.
- This is not a source-feasibility or market-edge verdict.
- The immutable terminal source snapshot is `research/source_snapshots/EA_QuotePathFidelityProbe_HYP-QPF-EURUSD-M1-002.mq5` with SHA256 `130E18ABB8AD29AAB17073BFAAF3DEF499FF95B9A8C8494C4FC3FB359E748434`.
- A fresh engineering reissue may keep the exact observable set, source gates, symbol, timeframe and window while adding only explicit tester-input bindings.
