# HYP-EIBB-XAUUSD-M15-001 — manual pre-build review

Verdict: `PASS_NUMERIC_SOURCE_SCREEN / REQUIRE_EVIDENCE_BOUND_SOURCE_PASS`.

The preregistered outcome-blind count produced 115,746 valid M15 aggregates,
1,290 valid initial-balance dates and 1,287 exact-next events. Cadence was
4.9337/week, LONG/SHORT was 664/623 and annual counts were
257/258/257/258/257. No outcome or post-event price was read.

The mechanism is distinct enough for one untuned baseline, but broad
price-only session breakout has adverse prior evidence. No filter, alternate
session, direction deletion, stop/target retune or same-ID rescue is allowed.

Before MQL5 build, the screen must be reproduced into a deterministic source
report, event ledger, receipt and terminal. Runtime must either reconstruct
M15 from the same native M5 constituents or prove exact native-M15 parity. The
selected implementation contract is direct M5-to-M15 reconstruction.

Reviewer scope was read-only: no file edit, MT5 run, strategy change or new
hypothesis.

