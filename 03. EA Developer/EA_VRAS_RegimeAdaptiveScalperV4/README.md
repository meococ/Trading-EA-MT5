# EA_VRAS_RegimeAdaptiveScalperV4

Research-only pre-EA review record. There is deliberately no `.mq5`, EX5,
AlphaFactory contract, compile, Strategy Tester run, or economic result in this
package.

The Owner-supplied three-engine build plan was reviewed under the frozen
`HYP-VRAS-EURUSD-M5-015` P0 contract. Its one outcome-blind preflight returned:

`PARK_PRE_EA_INVALID_PLAN_EVIDENCE_OR_CAPABILITY_NO_OUTCOME_READ`

The supplied headline Hurst/variance-ratio/OU values reproduce only on the
unfiltered USDJPY tail of a combined EURJPY/EURUSD/USDJPY DESIGN file. The plan
misstates both symbol identity and history coverage, transfers those values to
EURUSD, requires unavailable true-flow primitives, leaves estimator/arbitration
rules unspecified, and depends on an async kernel that is not production-ready.

Start with:

- `research/HYP-VRAS-EURUSD-M5-015_PREFLIGHT_READOUT.md`
- `research/HYP-VRAS-EURUSD-M5-015_FAILURE_PACKET.json`
- `research/HYP-VRAS-EURUSD-M5-015_PREFLIGHT_PLAN.md`
- `research/evidence/HYP-VRAS-EURUSD-M5-015_PREFLIGHT/preflight_result.json`

This closes only the supplied plan/evidence/capability object. It is not a
market no-edge verdict. A successor needs a materially new, atomic mechanism,
correct target-symbol evidence, a frozen estimator/null/power contract, genuine
causal flow data if flow is claimed, and a safe execution contract under a fresh
identity.
