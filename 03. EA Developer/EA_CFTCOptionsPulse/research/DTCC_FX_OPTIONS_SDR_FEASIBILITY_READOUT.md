# DTCC FX Options SDR Source Feasibility Readout

Date: 2026-07-16

## Scope

This was a source/schema feasibility check only. It did not open a hypothesis,
join MT5 price outcomes, calculate strategy performance, create an EA, compile
MQL5 or run Strategy Tester.

## Primary-source route

- Official public dashboard: `https://pddata.dtcc.com/ppd/cftcdashboard`
- Official PPD guide: `https://kgc0418-tdw-data-0.s3.amazonaws.com/gtr/static/gtr/docs/RT_PPD_quick_ref_guide.pdf`
- The public cumulative endpoint exposes roughly the latest 366 days.
- Older 2018, 2020 and 2023 CFTC FX objects exist, but their S3 metadata reports
  `DEEP_ARCHIVE` and no active restore; public GET is unavailable.

## Schema evidence

- Public samples for 2024-07-16 and 2025-01-02 were acquired on `D:` only.
- Both expose 110 fields, including call/put amount and currency, strike,
  premium, execution timestamp, action/event and UPI fields.
- The accessible samples contain 3,997 and 5,691 option-like rows.
- `Option Type` is blank in the sampled payload and the public schema does not
  expose buyer/seller aggressor. Call/put currency orientation must not be
  relabeled as signed demand.

## Verdict

`FAIL_7_YEAR_ACCESS_OBJECTS_BEFORE_2024_07_ARE_DEEP_ARCHIVE_WITHOUT_RESTORE`

The source cannot provide the 2017-2023 train/internal-validation history
required before a sealed 2024-2025 holdout. Current data volume does not repair
missing historical point-in-time coverage. No hypothesis, `.mq5`, compile,
Model 0 or live action is authorized from this result.

## Evidence identity

- `02. AlphaFactory/external/dtcc_fx_options_sdr/schema_probe.json`
  - SHA256 `1D0C63CD1CAA31A917536E0254F0BF19AD0D9DDA55A034ACCEF63B45E3422810`
- `02. AlphaFactory/tools/inspect_dtcc_fx_options_schema.py`
  - SHA256 `7D0090D25E45B566A0B6FCECFF927DA6E19B1820BC5719E0C5BDFE5B0E13423C`
- `02. AlphaFactory/tests/test_dtcc_fx_options_schema.py`
  - SHA256 `3A4AB076926C616B09A05F4ECE7EDBD649B97BFD74208A847A556EB4A750C468`

Price outcomes accessed: `0`. MT5 initialized: `false`. Performance metrics
produced: `false`. Workspace GOAL: `UNMET`.
