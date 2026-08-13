# HYP-IVRL-XAUUSD-M5-001 — source feasibility result

Verdict: `PASS_SOURCE_FEASIBILITY`

The sole outcome-blind source attempt completed with deterministic replay on
native FivePercent XAUUSD M5 DESIGN data `[2018-01-01, 2023-01-01)`.

- Design rows: `351,303`; complete sessions: `1,276/1,305` (`97.7778%`).
- Raw/executable events: `1,196/1,196`; exact-next coverage: `100%`.
- Cadence: `4.584885/week`.
- Direction: `607 LONG` (`50.7525%`), `589 SHORT` (`49.2475%`).
- Calendar years 2018..2022: `231, 238, 237, 242, 248`, or
  `4.4301..4.7562/week`; max-year share `20.7358%`.
- All frozen source gates pass. Outcomes, costs and economics were not opened.

This permits one untuned Model-0 economic baseline of the exact
late-variance-relocation continuation. It does not establish edge or promotion
readiness and does not authorize parameter/filter search.
