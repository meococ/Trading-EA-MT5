# HYP-GC-OFI-INNOV-XAU-M5-003 — Source-integrity terminal kill

## Verdict

`KILL_SOURCE_INTEGRITY_HYP003`

HYP003 is terminal at the frozen source gate. No candidate-event cadence, tail predicate, XAUUSD target outcome, economics, MQL5, MT5, optimization, validation, paper trading, live trading, or market-edge claim was opened.

## Frozen identity

- Run: `GCOFI003-Q1-2019-SOURCE-INTEGRITY-001`
- Dataset: Databento `GLBX.MDP3`
- Window: `[2019-01-01T00:00:00Z, 2019-04-01T00:00:00Z)`
- Raw GC instrument IDs: `32257`, `14651`, `142620`
- Source receipt: `02. AlphaFactory/data/databento/gc_order_flow_innovation/HYP-GC-OFI-INNOV-XAU-M5-003/GCOFI003-Q1-2019-SOURCE-INTEGRITY-001/source_integrity_result.json`
- Source receipt SHA-256: `877A9D9CEE6F35D50109F0CFC8BBFBB8890931EC3B33798DE41646A6676A6DE0`

## Failures

The analyzer decoded all `4,292,841` TBBO records. It excluded `307,199` records on the four preregistered degraded provider dates and inspected `3,985,642` eligible records.

1. Duplicate `(ts_event, sequence)` keys: `49,989`; frozen acceptance was exactly zero and duplicates could not be silently dropped.
2. `BAD_TS_RECV` or `MAYBE_BAD_BOOK` flag records: `5,323`; frozen acceptance was exactly zero.
3. Direct A/B aggressor volume share: `0.9860960694566356`, below the frozen `0.99` floor. Count share was `0.9912804511795088`, but both count and volume gates were required.
4. Conflicting definition records: `12`; the frozen source contract required an unambiguous raw-instrument definition.

Status coverage itself was complete for signed rows (`1.0`) and ordering violations were zero, but passing subchecks cannot override any fail-closed source gate.

## Boundary of inference

This verdict says only that the exact HYP003 GC TBBO source/estimator contract is inadmissible. It is not evidence for or against XAUUSD profitability. Deterministic estimator replay was not executed because the source gate had already failed; candidate-event count emitted and tail predicate evaluated both remained `false`.

## Next action

Do not revise thresholds, drop duplicates, ignore flags, or reinterpret definitions after seeing this readout. Return to a new, economically distinct mechanism and preregister its source and target contract before any outcome access.
