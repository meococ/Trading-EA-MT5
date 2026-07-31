# EA_EventCLOBPersistence

Research-only package. Current successor:
`HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002`.

Current state: `PARK_STAGE0B_DESIGN_SOURCE_OR_CADENCE`.

- Mechanism: scheduled point-release clock plus late persistent CME 6E MBP-10
  top-five depth imbalance; eventual execution venue is EURUSD M1.
- Outcome-blind Stage 0A: 630 point-release clocks over 2019–2022,
  3.01848 clocks per elapsed week; 329 design and 301 validation clocks.
- Owner approved USD 3.50 for exact plan `DEDDE7F2...0C16`. The design-only
  acquisition completed 658/658 requests under the ceiling at vendor live
  estimate USD 3.141317501659; 652 files were nonempty and six were explicit
  source-empty. Validation source and every EURUSD price outcome remained sealed.
- The reviewed outcome-blind Stage 0 analyzer passed 50/50 focused tests and
  produced a deterministic 329-event ledger. Coverage passed at 326/329 for
  PRE, LATE and paired nonempty source, but only one event passed the frozen
  source-quality and sign gates: cadence 0.009576/week versus required 2–5.
- Independent replay found zero artifact/math mismatch. The dominant failure
  was real event-driven MBP silence: 488/652 segments exceeded the frozen
  one-second gap limit. Eleven segments also violated exact event-clock bounds
  although receive-clock request bounds were correct.
- Stage 1, EURUSD outcome access, validation purchase, `.mq5`, Model 0,
  promotion, paper and live are forbidden for HYP-002. This is a source/feature
  supply PARK, not a market no-edge verdict.
- Calendar provenance is source-rank C and cost is an unverified event proxy;
  even a diagnostic survivor must replace both before promotion claims.

Canonical contract:
`research/HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_PROBE_PLAN.md`.

Terminal Stage 0 closeout:
`research/HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_STAGE0_PARK_CLOSEOUT.md`.

Parent HYP-001 quote/closeout remains immutable historical evidence.

Do not rescue this ID by relaxing gap/staleness/bounds, changing PRE/LATE,
selecting event subsets or opening outcomes. A successor needs a materially new
mechanism/data contract and a fresh ID/preregistration.
