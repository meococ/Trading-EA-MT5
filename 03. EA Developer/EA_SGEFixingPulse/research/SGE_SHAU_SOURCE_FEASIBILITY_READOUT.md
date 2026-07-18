# SGE SHAU fixing source-feasibility readout

State: **KILL_AT_SOURCE_GATE_NO_POINT_IN_TIME_PUBLICATION_PROOF**  
Economic hypothesis registered: **no**  
Price outcomes accessed: **no**  
Holdout 2024-2025 loaded: **no**

## Result

The official Shanghai Gold Exchange archive is dense enough for the book, but
it is not point-in-time auditable enough to authorize a preregistration or an
outcome join.

| Gate | Evidence | Verdict |
|---|---|---|
| Train density 2017-2021 | 1,209 final-PM dates; max one/day = 4.642/week | PASS |
| Validation density 2022-2023 | 484 final-PM dates; max one/day = 4.647/week | PASS |
| Session integrity | 2 anomalous dates among 1,695; both fixed skips | PASS |
| Official publication time + timezone | Article pages expose trade date only | FAIL |
| First-publication lineage | No official first-published snapshot or manifest | FAIL |
| Revision lineage | No official version/revision history | FAIL |
| HTTP temporal metadata | Three sampled articles had no `Last-Modified` or `ETag` | FAIL |

The fixing mechanism itself is real: the SGE rules require Fixing Members to
absorb the unmatched allocation and describe 10:15/15:00 China-time sessions.
Those rules establish a causal auction mechanism, but do not prove when each
historical detailed BID/ASK/supplemental-balance table first became publicly
available.  The public article HTML labels only `time: YYYY-MM-DD`; sampled
responses on 2017-01-03, a mid-archive date, and 2023-12-29 had neither an
immutable object version nor a publication timestamp.

A T+1 08:05 London entry buffer would therefore be a research assumption, not
point-in-time provenance.  It cannot be used to rescue the source gate.

## Integrity

- Official archive acquired to D only: 1,695 articles / 94,555,139 bytes.
- Parsed rows: 10,617; valid final-PM dates: 1,693; range 2017-01-03 through
  2023-12-29.
- Acquisition/parser/profile tests: 6/6 PASS.
- Source CSV SHA256:
  `379058EA03167BCD723A370C4E6ACF8EA7F89EFC707E2B2CA25F17CDD52357C8`.
- Fail-closed profile SHA256:
  `EA3FD531A068B10757CE8BC17BB9BA5DA9E75B9DDA0C28EFED9D95F885CD90CF`.
- Profiler SHA256:
  `6A3E2C694C07EDD856B6C7F3BFE826540A0BCAD5EF85496C7A1A5A54CB361F44`.
- Current 2024/2025/2026 endpoint checks were schema/magic smokes only; no
  values were retained or interpreted.

Primary official surfaces:

- Rules: <https://en.sge.com.cn/upload/file/202001/17/RnByn7qMIWiZca3s.pdf>
- Current SHAU data: <https://www.sge.com.cn/sjzx/shanghaiAuAuto>
- Historical archive: <https://www.sge.com.cn/sjzx/shjzjhq>

## Verdict

Do not infer a publication time, scrape outcomes, freeze a directional rule,
create an EA, compile, or run MT5 for this source.  Compile/backtest would test
code built on unauditable historical availability and would not count toward
`01. GOAL/GOAL.md`.

The lane may reopen only with official historical `published_at` timestamps
and immutable first-publication/revision lineage, or a legally archived
point-in-time vendor dataset approved as a new source contract.
