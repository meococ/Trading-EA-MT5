# HYP-TRENDSTACK-EURUSD-H1-007 - PROBE PLAN V5

Status: `FROZEN_IDEA_AMENDMENT_PRE_SOURCE_PRE_ECONOMICS`

This create-new amendment supersedes V4 SHA256
`B82673A0D1F492D9BBFA0EA044EBA8B55F33ADFE614E58F62C71FD936CA3D80E`.
V1 through V4 remain immutable evidence. No HYP007 public Parquet shard, OHLC,
return, PnL, performance metric, VALIDATION, or HOLDOUT payload was opened
before this V5 freeze.

The active source contract is V4 SHA256
`2F3D071F5E079B49B5705D47BABFFCC7F65998744AA0E1E9352389F89EA1EADB`
plus the single fail-closed additive rule in
`HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_CONTRACT_V5.json`.

Every staged output Parquet shard must have Arrow `schema_arrow` exactly equal
to V4 `physical_arrow_schema` in field names, order, physical types, and
nullable flags, with Parquet metadata ignored. Extra, missing, reordered, or
retyped fields are engineering-invalid. All V1-V4 economic, source, authority,
validation, lifecycle, adverse-prior, and no-rescue rules remain unchanged.

V5 grants no source build or run by itself and no economics or sealed access.

