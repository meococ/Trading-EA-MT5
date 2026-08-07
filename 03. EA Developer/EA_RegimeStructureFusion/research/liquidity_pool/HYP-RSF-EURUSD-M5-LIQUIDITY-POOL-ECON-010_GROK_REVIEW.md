# Independent Grok review — HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010

Reviewed: 2026-08-07

## Runner evidence

- Backend: Grok Build CLI, `grok-4.5-build`
- Contract: read-only, local-only, no web, no subagents, no new economics or edits
- Stop: `EndTurn`; schema validation: PASS; turns: 9
- Response SHA256: `DEDFEC19386FB475B7BF94DC62B5EE7DE81FC770C5CE698E1C9C8FEB302A91BB`
- Summary SHA256: `FAC71BEF8008645DE14BBDE220218C2A055B7A7B079BAA944F81B5FECC15B1B6`
- Canonical runner artifacts:
  `.context/rsf-liquidity-pool-econ-010-independent-review/run3/`

An earlier eight-turn attempt ended `Cancelled / max turns reached` and is not
accepted as a review result. Only `run3` is authoritative.

## Independent verdict

Grok confirms:

- engineering-valid: yes;
- economic-valid: no;
- promotion-ready: no;
- legal next test under HYP-010: none;
- parameter/timezone/direction/session/engine/RR rescue: forbidden.

The independent review classifies the dominant failure as strategy-edge
failure, not a broken report or reconciliation path. It verified the source,
report/config hashes, zero TB snapshot failures, 162 OPEN/162 final CLOSE
reconciliation and the negative full-population economics.

## Findings retained by the Lead Quant

1. **P0 — base economics fail:** N162, PF0.714519, net -USD3,981.17,
   -0.136032R mean and negative expectancy. This alone kills HYP-010.
2. **P1 — no legal subset rescue:** Europe and New York both lose. The
   post-outcome breakout-long slice remains below PF1.30 with near-zero mean R.
3. **P1 — mechanism executed as designed:** causal closed-bar TB pool, runway
   checks and sidecars worked; correct plumbing did not create edge.
4. **P2 code defect — arm-time objective staleness:** 12/162 entries had a
   nearer still-live pool level at entry than the objective frozen when the
   event armed. Direction remained valid and no below-1.25R objective was
   accepted, so this is not lookahead/repaint and does not invalidate the kill.
   Rebinding would alter the decision surface and requires a fresh ID; it is not
   a legal HYP-010 rescue.
5. **P2 — QQE veto inert:** zero timing rejects across the tested population.
   The chart casebook cannot authorize mining a new threshold.
6. **P2 evidence boundary:** the 21 sequence tests are static source-contract
   tests. Runtime engineering confidence also depends on RunMeta and exact
   sidecar reconciliation; the tests alone are not a dynamic non-repaint proof.

## Chart scope

Grok reviewed the written native MT5 casebook and verified the eight PNG hashes;
it did not receive image pixels and made no independent visual or TradingView
parity claim. The Lead Quant separately inspected all eight native screenshots.

## Decision

The independent findings strengthen, rather than soften, the terminal verdict.
HYP-010 remains closed. The known P2 objective-rebinding issue is carried as an
engineering debt item for a materially new hypothesis, not patched and retested
post hoc under this ID.
