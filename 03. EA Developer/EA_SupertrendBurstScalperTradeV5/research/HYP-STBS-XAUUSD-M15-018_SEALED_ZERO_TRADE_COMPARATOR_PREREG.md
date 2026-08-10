# HYP-STBS-XAUUSD-M15-018 — sealed zero-trade comparator preregistration

Status: `FROZEN_PRE_AUTHORITY`

## Thesis and scope

HYP018 is a fresh comparator-only engineering child of terminal HYP017. It does
not compile MQL5, launch MT5, read market data, submit orders, or open economic
analysis. Its only purpose is to replay the already captured immutable HYP017
run inventory after HYP017's frozen runner stopped on a stale expected data
fingerprint.

The strategy, signal, ATR, geometry, risk and account logic are unchanged. A
PASS can establish only `PASS_ENGINEERING_ZERO_TRADE_MODEL0_AUDIT`; it cannot
establish profitability, PF, expectancy, robustness, or deployment readiness.

## Immutable inputs

Only files under this root may supply HYP017 run evidence:

`02. AlphaFactory/runtime/model0_audit_attempts/HYP-STBS-XAUUSD-M15-017/STBS017-MODEL0-AUDIT-001/failed_run_inventory/20260810_002304`

The comparator must bind and capture once the run manifest, report, journal,
source snapshot, EX5 snapshot and config snapshot. It must also bind the
HYP017 task/receipt/start/terminal, its frozen quant parser, this preregistration,
the comparator test, terminal HYP017 raw row, and the pre-outcome HYP013 data
fingerprint provenance.

The accepted data fingerprint is exactly
`B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25`.
It was frozen before HYP013 outcomes in task packet SHA256
`DE25AE28B29087901514B1ABA067A00B8DF05F7F4288CF93D79188A730255DE9`,
preregistration SHA256
`EF3DB79293438056A1634723E5F2DAE7183E093EF33A6F84CC6E061AC4AFE1CA`,
and research cost-source manifest SHA256
`77A7D738AD945AB869CC1682110FF64C1DC3D8827039F68F937392A793C7CAF8`.
The exact screened pre-execution HYP013 registry row is SHA256
`5A957E169AEF9DF420534FE4A242E0ABC81F58FB2F80070AED4A4148047FD837`;
it must bind those files and predate the HYP017 durable start.
This is provenance correction, not outcome-driven data selection.

## Frozen acceptance

The manifest must retain outer HYP017 and inner MQL HYP016 identities, XAUUSD
M15, 2005.01.01–2023.01.01, Model 0, deposit 100000, leverage 100, current
spread, telemetry none/off, exact effective overrides, exact source/EX5/config/
report/receipt hashes, and broker/server/account fingerprints.
The HYP017 run compile log must be SHA256
`886A9883DEDC54D2FC8236B8075A72FD1CDF61F8C407DE32E8402E95110300E6`
and contain exactly one `Result: 0 errors, 0 warnings` record. Manifest paths
must identify the exact original run-local report/source/EX5/config snapshots,
while comparison reads only their attempt-local immutable copies. The failed
inventory file set is exact; any added sidecar or file fails.

Data quality must be HQ 98 with full fixed-window coverage and exact series
proof. Journal provenance must be: `files_read=3`, `bytes_read=857818`,
`exact_match_count=2`, `distinct_range_count=1`, `truncated=false`, exported
SHA256 `3284EA885A965123FB0BDA1B51F126524F014C1ABD95D43BDCF66E222A9361CE`
and size 428908 bytes.

Exactly two identical `STBS_SUMMARY` rows with `reason=1` are required. MQL5
defines reason 1 as removal from the chart. Exactly 1,380 signal records must
normalize to 690 unique events with uniform multiplicity two: executable 683,
gaps 7, LONG 339, SHORT 344, ATR/geometry/margin-ready 683, zero rejects,
emergencies, stopouts, entries, closes, lifecycle rows and runtime failure.
Every exact signal must prove decision=source+3600, positive volume,
required_free=93600 and projected_free>=required_free. Every gap must be
consumed. Forbidden request/deal/fatal markers fail.

The report must have an exact-empty Orders section, exactly one initial funding
balance row at 2005-01-01 for 100000, and zero completed trades. No sidecar,
order, deal, return, PF or outcome evidence may be created or accepted.

The analysis is replayed twice from the same captured bytes and must serialize
identically.

## One-shot and authority boundary

The sole attempt is `STBS018-COMPARATOR-001`. Its durable exclusive claim is
created before registry or artifact reads. Success or failure writes an
exclusive terminal and consumes the attempt. Same-ID retry and registry
mutation are forbidden.

All MT5, AlphaFactory run, compilation, source-data, trade, outcome,
performance, economic, optimization, validation, holdout, promotion, paper and
live authorities remain false. A PASS unlocks only a fresh, separately frozen
trade-enabled economic child.
