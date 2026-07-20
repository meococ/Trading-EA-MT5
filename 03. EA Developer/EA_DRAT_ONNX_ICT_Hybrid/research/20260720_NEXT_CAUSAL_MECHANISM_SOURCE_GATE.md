# Next Causal Mechanism Source Gate

Date: 2026-07-20

Status: `LEGAL_SOURCE_FEASIBILITY_PROBE_BLOCKED_ON_LOCAL_API_KEY`

This readout selects a data-acquisition route only. It does not register or
reopen a trading hypothesis, define entries/exits, read price outcomes, inspect
PnL, authorize EA/ONNX source changes, or permit Strategy Tester work.

## Frontier inherited from the current workspace

- The EURUSD M5 ICT/FVG confirmation, human-context, tick-initiation,
  level-path, level-resilience and pivot-dwell lineage is terminal at HYP-026.
- A successor may not reuse those measurements as a filter, threshold,
  management rule or subgroup rescue.
- The next legal lane must add a materially new point-in-time information set
  with a plausible causal connection to EURUSD.

## Official-source verification

| Route | Verified fact | Source-gate verdict |
|---|---|---|
| Databento `GLBX.MDP3` CME EUR/USD options | Databento documents free metadata and symbology access, pre-request `metadata.get_cost`, parent symbology, and charged time-series access. `definition` supplies point-in-time security definitions; `statistics` includes exchange session/daily statistics and open interest. | `LEGAL_PROBE_PAID_UNLOCK`: source feasibility only, under the frozen acquisition contract and an explicit Owner USD ceiling. |
| Official scheduled macro surprise | Official statistical agencies publish releases/actuals and some vintage histories. The ECB SPF is quarterly; it is not the historical pre-release consensus for every CPI/NFP/GDP print and cannot mechanically support the intended event cadence. | `DATA_BLOCKED`: no free reproducible point-in-time consensus lineage was verified for the required per-release object. |
| LSEG FTSE Russell WMR FX benchmark | The WMR methodology is public, while benchmark data are distributed through LSEG platforms, feeds/APIs and authorized vendors. No free point-in-time historical directional flow, order or imbalance input was verified. | `DATA_BLOCKED`: a public calculation methodology or published fixing level is not the missing directional input. |

Primary sources:

- https://databento.com/docs/api-reference-historical
- https://databento.com/docs/standards-and-conventions/symbology
- https://databento.com/docs/knowledge-base
- https://www.ecb.europa.eu/stats/ecb_surveys/survey_of_professional_forecasters/html/index.en.html
- https://www.lseg.com/en/ftse-russell/benchmarks/wmr-fx-benchmarks

The in-app Deep Research attempt was stopped and rejected as evidence because
its search expansion confused `GLBX` and `WMR` with unrelated entities. Only
the direct official sources above and local executable checks support this
readout.

## Selected route and frozen boundary

Select only the existing Databento route defined by
`20260716_CME_EURUSD_OPTIONS_ACQUISITION_CONTRACT.md`:

- dataset: `GLBX.MDP3`;
- schemas: `definition` and `statistics`;
- option universe: resolved current and legacy EUR/USD option parents plus
  `6E.FUT`;
- coverage: `2020-01-02` through `2026-06-30`, inclusive;
- storage: ignored D-side tree
  `02. AlphaFactory/external/cme_fx_options_euro/`;
- no CVOL requirement; implied volatility, skew, term structure and convexity
  are not raw vendor fields assumed by this gate and may only be derived under
  a later frozen feature contract.

The 2020 start is deliberate and matches the existing acquisition contract. It
does **not** prove or represent the earlier 2018--2019 period used by the ICT/FVG
chart backtest. Expanding the licensed order to 2018 would require a new
pre-charge V2 coverage decision and cost estimate before submission.

## Outcome-blind source-feasibility probe

After the raw batch is downloaded, inspect only data identity, publication
timing, chain continuity and mechanical cadence. Do not join EURUSD future
returns or any EA trade outcome.

Required validations:

1. Every raw file has immutable relative path, byte size and SHA-256.
2. Dataset/schema/account range and requested coverage are copied into a
   hash-bound manifest; API keys and account secrets are absent.
3. Security definitions retain their original event timestamps, raw symbols,
   instrument IDs, asset/root, instrument class, strike, put/call, expiry,
   underlying reference and price scaling where supplied by the schema.
4. Statistics retain their original event timestamps, instrument identity,
   statistic type, price/quantity and exchange sequence/flags where supplied;
   settlement, cleared volume and open-interest availability must be proven
   from actual records rather than inferred from schema names.
5. Current and legacy parent resolution is reconciled to raw instruments.
   `6E.OPT` alone is not accepted as proof of complete weekly/monthly coverage.
6. Calls and puts, multiple expiries and the underlying future are present in
   every covered calendar month. Missing or partial parent intervals remain
   visible in the manifest.
7. Causal availability uses the first EURUSD decision bar strictly after the
   official statistic/definition event time. Previous-day open interest is not
   relabelled as same-day information.
8. Mechanical cadence counts unique causal availability dates, never option
   contracts. At least 90% of complete elapsed weeks must contain 2--5 distinct
   availability dates; this gate proves only that the source can support the
   workspace cadence, not that a future strategy will trade that often.
9. Identity fields must be 100% defined. Required economic fields must be at
   least 99% defined on eligible chain-date rows, with missingness reported by
   year, parent/root, option side, expiry bucket and statistic type.
10. Re-running normalization and profiling with the same raw hashes and seed
    must reproduce identical row counts, coverage tables and artifact hashes.

Stop immediately with `SOURCE_GATE_FAIL` if any required schema is absent, no
EUR/USD option parent resolves, actual records cannot prove settlement/volume/
open-interest semantics, chain continuity or publication timing cannot be
reconciled, the 90% cadence gate fails, or raw identity/replay hashes differ.

## Executable state on 2026-07-20

- `test_databento_fx_options_acquire.py`: `5 passed`.
- Installed D-side Databento SDK: `0.54.0`; inspected method signatures match
  the planner calls used for metadata, symbology, cost, billable size and batch.
- `plan` exits before client creation because `DATABENTO_API_KEY` is absent.
- No time-series request, batch job, download or charge occurred.
- The plan/submit implementation re-estimates cost and blocks all jobs when the
  live total exceeds the explicit Owner ceiling.

Minimum external unlock:

```powershell
& '.\02. AlphaFactory\tools\configure_databento_key.ps1'
```

The key must be typed into the hidden local prompt and never pasted into chat.
After configuration, the next allowed action is the metadata/symbology-only
`plan`. Submission remains prohibited until the Owner separately approves a
numeric USD ceiling after seeing that plan.
