# HYP-VRAS-USDJPY-M5-001 — cost evidence preflight

## Evidence inventory

- The bound USDJPY M5 foundation parquet contains a historical `spread` column
  with exact server/UTC timestamps for the TRAIN window.
- No USDJPY cost-source manifest exists in `03. EA Developer`.
- No hash-bound USDJPY same-symbol commission sample or explicit broker contract
  exists in the workspace.
- No independent-reference USDJPY fill evidence, or qualifying independent
  executable-quote slippage sample, exists in the workspace.

## Fail-closed decision

The preregistered `0.70` commission-pip and `0.30` one-way slippage inputs are
engineering stress assumptions, not verified provenance. They may protect entry
geometry but cannot authorize economic metrics.

Verdict:
`PARK_PRE_MODEL0_MISSING_USDJPY_COMMISSION_AND_SLIPPAGE_PROVENANCE`.

The source, compile, tests, and non-repaint audit remain engineering-valid.
Model-0 performance, economic validity, promotion, paper, and live authority
remain false. Creating a `VERIFIED` or `VERIFIED_RESEARCH_PROXY` manifest from
assumed numbers would be evidence laundering and is forbidden.
