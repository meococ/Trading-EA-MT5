# HYP-TLB-XAUUSD-M15-001 — source result

Verdict: `PARK_SOURCE_FEASIBILITY_OVER_FREQUENCY_NO_ECONOMIC_READ`

- Exact standard Three-Line Break reversal mapping on XAUUSD M15, DESIGN
  2018–2022.
- Aggregated M15 rows: `115,746`; exact-bucket coverage `98.8429%`.
- Confirmed Line Break lines: `26,136`.
- Raw reversals: `5,200`; exact-next executable reversals: `5,171`.
- Cadence: `19.8231/week`, failing the frozen `2–5/week` gate.
- LONG/SHORT: `2,584/2,587`; exact-next coverage `99.4423%`.
- Year counts: `1,027 / 1,010 / 1,021 / 927 / 1,186`; every year is
  `17.78–22.75/week`, so the failure is structural rather than one year.
- Deterministic replay passed. No post-decision price, trade, return, cost, PF,
  validation or holdout was opened.

Failure radius is only the exact `3`-line reversal state machine defined in the
frozen prereg. Do not rescue it with a line-count change, daily quota, cooldown,
session/weekday filter, direction deletion or threshold. A fresh mechanism must
use a materially different information family.
