# HYP-XJRR-XAUUSD-M5-001 — source-feasibility result

Verdict: `PASS_SOURCE_FEASIBILITY_IMPLEMENTATION_REVIEW_ONLY`

Authoritative attempt: `XJRR-SOURCE-002`.

- Joined synchronized XAUUSD/USDJPY M5 rows: `351,266`.
- Feature and exact-next coverage: `100% / 100%`.
- Executable source opportunities: `1,290` (`614 LONG / 676 SHORT`).
- Frozen cadence upper bound: `4.945235/week`.
- Calendar-year counts: `257 / 258 / 259 / 258 / 258`.
- Conflicts, Friday-20 blocks and forbidden outcome fields: `0 / 0 / 0`.
- Outcomes, returns, costs, PF, validation and holdout were not opened.

Evidence hashes:

- report: `E778EEE072AEE8BDC536AE98D89F0331937FFB8EF5D12A0F95920B675C6943BE`
- ledger: `DFF7CB591CB091CA86ACC1B62A37105F661EFAB5EBC0DA8155ACD2C3C26753B3`
- receipt: `67FF4AB6997BF09556D70463551F0AEC77682358584EB7F29C58F65FA21AB958`
- terminal: `911BE81FBEBA2F1CADBCFA81AB6AA72DB68E312A78C679897F1DE525F18DA63A`

The 1,290 events are exactly one per 1,290 server dates. Therefore this result
is an opportunity-population upper bound created by the preregistered daily
consumption rule, not proof of completed-trade cadence or edge. MQL5 must
consume the daily slot before overlap, exact-next, Friday and geometry checks;
only the untuned baseline may establish completed cadence and economics.
