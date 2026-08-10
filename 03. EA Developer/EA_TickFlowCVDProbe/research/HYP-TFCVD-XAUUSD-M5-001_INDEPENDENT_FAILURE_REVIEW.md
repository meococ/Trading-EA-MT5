# HYP-TFCVD-XAUUSD-M5-001 — Independent Failure Review

Date: 2026-08-09  
Reviewer: independent read-only sub-agent `t2_campaign_audit`  
Scope: frozen preregistration, exact source, analyzer, tests, run manifest, MT5 report/journal, source analysis and terminal verdict. The reviewer changed no files.

## Verdict

`KILL_SOURCE_FEASIBILITY_EXACT_TICK_DELTA_MAPPING` is correct with high confidence. It kills only the frozen FivePercent XAUUSD M5 2018–2022 broker-native quote-delta mapping. It does not establish an economic no-edge conclusion and does not kill all flow-based mechanisms.

The decisive evidence is independent of the zero-candidate count:

- the frozen contract requires History Quality strictly above 97%; the report records 0%;
- the tester journal says FivePercent XAUUSD real ticks begin on 2026-06-01, so the frozen historical window used generated ticks;
- the exact run was zero-trade and the manifest binds the executed source and binary;
- generated ticks cannot support the broker-native quote-arrival thesis.

No same-ID rerun, threshold relaxation, generated-tick acceptance, window change or economic read is justified.

## Implementation findings

No fatal lookahead or trade-path defect was found. The collector is causal, finalizes a bar only after a later M5 bar begins, intentionally omits the last unproven bar and has no order path.

Successor implementations must close these gaps:

1. `ResetBarCounters()` does not reset prior Bid/Ask/mid or last polarity. The first update after a bar boundary or weekend therefore compares against the preceding bar, while an unchanged mid can inherit stale polarity. This is causal but the continuous-versus-per-bar polarity contract was not explicit.
2. The collector does not use `time_msc` and `OnTick()` plus one `SymbolInfoTick()` read cannot prove every same-bar quote was captured in order. A future real-tick collector needs a millisecond cursor and `CopyTicks` reconciliation.
3. The analyzer accepts History Quality as a caller-supplied scalar instead of deriving and binding it to report, journal and tester model. It also does not independently enforce exact coverage, real-tick provenance, zero trades, gap/bar-end consistency or accounting identities.
4. Tests omit bar-boundary polarity, weekend gaps, same-bar timestamp ordering, provenance binding and malformed accounting cases.
5. The screened EX5 hash differs from the executed manifest-bound EX5 hash while the source identity is exact. This is a low-severity build reproducibility/receipt gap, not evidence of source drift and not grounds to reverse the kill.

## Evidence strength and next lane

- Exact historical source-feasibility kill: conclusive.
- Zero candidates as evidence against true broker quote flow: weak and unusable because the ticks were generated.
- Economic edge conclusion: unauthorized; no outcomes were opened.

The safest flow successor is forward-only real-tick acquisition with immutable `time_msc`, Bid, Ask, spread, flags and daily hashes. Because that route needs a long observation horizon, the immediate historical research lane may use native MT5 M1/M5 tick volume only as **unsigned broker activity**, not trade volume or aggressor flow. Its first pass must be outcome-blind source/cadence feasibility, and live observed costs must be acquired before economics because the existing bar-data spread column is not cost truth.

