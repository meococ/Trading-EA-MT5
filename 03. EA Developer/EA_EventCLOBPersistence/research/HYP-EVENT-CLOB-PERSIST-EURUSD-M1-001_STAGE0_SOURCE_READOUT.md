# Stage-0 Source Readout — HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001

Status: `PARTIAL_SOURCE_GATE_QUOTED_PAYMENT_AUTHORITY_UNMET`

This is an outcome-blind source readout. No CME time-series data, EURUSD price
outcome, PnL, PF, expectancy, MFE/MAE, MQL5, MT5 Model 0, paper order or live
order was opened.

## Decision

The fresh EVENT-CLOB candidate remains alive but is not yet eligible for an
economic probe or EA build.

- Stage 0A clock supply PASS: 630 frozen point-release clocks over 208.7143
  elapsed weeks, or 3.01848 clocks/week; design 329 and validation 301.
- Free metadata quote PASS: 630/630 windows, estimated USD 7.005795553319 and
  15,044,831,392 billable bytes (14.0116 GiB).
- Storage capacity PASS: D: had 402.23 GiB free at assessment time; the target
  raw directory was absent and cleanup dry-run found zero candidates.
- Payment authority UNMET: no positive Owner USD ceiling is bound to the quoted
  plan. The paid path remains fail-closed. The final V8 quote needed one
  transient free-metadata retry (`get_cost=631`, `get_billable_size=630`).
- Stage 0B source coverage UNOPENED: zero raw DBN files and no download manifest
  exist, so source eligibility/cadence and all economic gates remain unknown.

Recommended bounded ceiling if the Owner chooses to proceed: **USD 7.75**,
which is 10.6% above the live estimate. The tool performs another free live
re-quote under an exclusive filesystem lock and stops before the first paid
call if the new estimate exceeds the explicit ceiling.

## Frozen mechanism and controls

- Event population: scheduled external point-release clocks, not a price-break
  subgroup and not a post-hoc event-name/hour filter.
- Challenger information: persistent same-sign CME 6E top-five MBP-10 depth
  imbalance in the late event minute, with a fixed pre/late change check.
- Direction control: first completed EURUSD M1 event-bar direction on the same
  eligible population, risk geometry, costs and 15-minute exit.
- ATR30 is pre-event risk normalization only; it is not a directional filter.
- No threshold grid, indicator stack, TP, break-even, trailing, session veto or
  management rescue is authorized under this ID.

## Hash-bound evidence

- Frozen probe plan SHA-256:
  `D47615E32F1E374D3CBFB23EA2DD9ABF594A85F2E22BF1C3CD5B08D60B6F5011`.
- Frozen clock SHA-256:
  `5C30F99FF0E1341D680C2747315E2FF4DFF99C5FBE01C2C5C4036BC101375E7B`.
- Bound registry row SHA-256:
  `F120C70E6D8AEB1C7194D599E970721946C32DACFA2EEDA6BAE0C4B4B811FAA3`.
- V8 task packet SHA-256:
  `5208D76C2F95BE3BDD6E4C7EB4B44A769CA323936F6F4B6AE931CA6525E8A2CC`.
- Acquisition tool SHA-256:
  `D540DBACECC3E32179142B307E18B0C773B3862732222CF6381FBD57E60A09B2`.
- Focused tests SHA-256:
  `2283A863A6BE6A40DBBEA57EE1C41624F66DD70B2B96D7E6FA64754D0EB579F5`;
  independent parent and reviewer runs both passed 42/42.
- Quoted plan ID:
  `F8CC58697DAF05713DCD4A4D0DDF1AA3DE9684A3DF646AE9C8F424F645851BDB`;
  plan SHA-256:
  `969AD05FEC3F99D6219C8387F9BE3F7C1C5A44624816E3106ADFB2FD1716DDAB`.
- Free quote receipt SHA-256:
  `0CCF146D9C3E2DB0E7ABFE00BD3C405D59F2A46871985B2FCA8B0DD80AAC4107`.
- Predownload storage assessment SHA-256:
  `AAFF8417D6E58738E1A826595E8BABE256EFE6429B98658CA97429337AA09006`.

Receipt validation passed with 631 `metadata.get_cost` attempts (one bounded
transient retry), 630 `metadata.get_billable_size` attempts, one dataset-range
call and one symbology call.
Every time-series and batch counter is zero and `paid_request_made=false`.

## Engineering review closeout

The first implementation was rejected by an independent Codex reviewer for
four fail-closed defects: canonical-window mismatch, receipt/plan drift,
unverified resume manifests and no exclusive paid lock. V4/V5 fixed all four
with red-first tests. V6 then removed only an unrelated append-only global
registry race from the free-quote boundary while retaining exact bound-row and
frozen-artifact checks. Paid download rechecks the exact global registry after
the live re-quote and before `timeseries.get_range`. Final independent verdict:
PASS, no remaining actionable finding in scope. V8 then added bounded retries
only for free metadata 429/502/503/504/timeout/connection errors; permanent
errors fail immediately and paid/batch paths cannot use the retry helper.

## Next legal transition

1. Owner explicitly supplies a positive USD ceiling bound to quoted plan ID
   `F8CC5869...1BDB` (recommended: USD 7.75).
2. Run one serial paid download under the exclusive lock. No automatic retry is
   allowed for an unresolved or empty charged response.
3. Hash and fully validate every DBN file; stop before EURUSD outcomes unless
   Stage 0B coverage, quality and cadence all pass exactly.
4. Only a Stage 1+2 economic survivor may authorize `.mq5`, compile, Model 0,
   log/chart forensics and Heavy-Delivery. The workspace goal remains UNMET.
