# HYP-TRENDSTACK-EURUSD-H1-007 - PROBE PLAN V6

Status: `FROZEN_IDEA_AMENDMENT_PRE_SOURCE_PRE_ECONOMICS`

This create-new amendment supersedes V5 SHA256
`0D143CE01DF6C97397C852B40177A47654FB36411E011A8BE4B91307AA04B099`.
V1 through V5 remain immutable evidence. No HYP007 public Parquet shard, OHLC,
return, PnL, performance metric, VALIDATION, or HOLDOUT payload was opened
before this V6 freeze.

The active source contract is the self-contained V4 SHA256
`2F3D071F5E079B49B5705D47BABFFCC7F65998744AA0E1E9352389F89EA1EADB`,
the exact output-schema addendum V5 SHA256
`8B9B6391A79E699DB21A80D14223B6ACAA24287390ECE4A0D8602DD758F4631C`,
and the exact metadata-hash-map addendum
`HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_CONTRACT_V6.json`.

V6 closes only the validation-to-publish metadata mutation surface. All six
stage metadata files must have exact uppercase-SHA maps in the validation
receipt and pass terminal. The supervisor rehashes all six immediately before
atomic rename and again after rename; both maps must equal the validator's map
exactly. Any missing/extra key, non-SHA value, mismatch or mutation is
engineering-invalid and forbids publish.

All V1-V5 economic, source, authority, lifecycle, adverse-prior and no-rescue
rules remain unchanged. V6 grants no build/run or economic/sealed access alone.

