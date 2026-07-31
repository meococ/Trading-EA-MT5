# SOURCE PLAN - HYP-EURFXOFI-EURUSD-M1-002

Frozen on `2026-07-30`, before any paid CME 6E request, order-book decode,
OFI feature result, target-return join or economic evaluation under V2.

## Owner decision and amendment scope

The Owner authorized a hard total source-acquisition ceiling of `USD 2.25` for
`HYP-EURFXOFI-EURUSD-M1-001` and expanded the requested research horizon from
`2016-2020` to `2016-current` in the same message. The append-only registry
forbids changing HYP001 after it reached `parked`, so this materially new clock
and horizon contract is recorded as its fresh successor HYP002. HYP001
completed only free metadata quotes and made zero paid, timeseries or batch
calls. HYP002 does not create a second budget: every paid cent under HYP002
counts against the Owner's single USD 2.25 ceiling for this successor work.

The USD ceiling is not a spending target. A live quote above `USD 2.25`, an
incomplete quote, source drift, or any contract mismatch must stop before the
first paid call. No automatic paid retry is permitted after an in-flight call.

## Clock correction and source boundary

The V1 date ledger came from a legacy parquet whose field `time_utc` directly
encoded the broker wall-clock epoch. A reconciliation against the canonical
full-history source found exact close equality for all `1,859,939` shared
EURUSD rows when legacy `time_utc` was matched to canonical `time_server`, not
canonical `time_utc`. A live read on 2026-07-30 also observed the FivePercent
raw tick/bar epoch at broker UTC+3 while the host UTC clock was current.

V2 must therefore rebuild the signal-date population from the canonical,
clock-corrected source and must not reuse the 612-date V1 ledger or V1 quote as
purchase authority.

Bound inputs:

- M1 parquet: `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`
  SHA256 `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- Manifest: `02. AlphaFactory/data/fivepercent/EURUSD/manifest.json`
  SHA256 `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`
- Pull audit: `03. EA Developer/EA_HybridRegimeMR/research/evidence/EURUSD_PULL_AUDIT.json`
  SHA256 `C21B5BC82681261FBED6681A1505B8B4D6AB8DAEA6571CCE814C46B9E99AA410`
- Clock model: `02. AlphaFactory/tools/research/fivepercent_server_clock.py`
  SHA256 `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`

Only exact completed `07:59` and `14:14 Europe/Berlin` M1 closes may enter the
date selector. The base parquet query projects only `time_utc,close` at those
exact target timestamps. To reach current, the production selector may use the
read-only D-side FivePercent terminal to request those same two exact M1 bars
for dates after the last complete canonical day through the latest fully
completed Europe/Berlin calendar day. It may not request the `15:59` exit or
any other post-decision price.

## Frozen signal-date rule and partitions

- Population starts `2016-01-01`; 2015 exact-slot observations are lookback
  seed only.
- Pressure = `(close_14:14 - close_07:59) / 0.0001` pips.
- Threshold = strict-lag median absolute pressure over the preceding 60
  complete weekdays, excluding the current day; minimum history 40.
- Select when absolute pressure is at least the threshold and pressure is
  non-zero. Missing either exact boundary skips that date. No nearest bar,
  fill-forward, calendar veto or outcome-dependent filter is allowed.
- `TRAIN`: 2016-2020; `VALIDATION`: 2021-2024; `HOLDOUT`: 2025-current.

All three partitions may be acquired and source-validated outcome-blind, but
economic target returns remain sealed and must be opened sequentially:
`TRAIN -> VALIDATION -> HOLDOUT`, with the prior partition passing its frozen
gate before the next one opens. A pooled 2016-current in-sample score is
forbidden.

The V2 selection should remain near the already inspected outcome-blind base
population (`603 TRAIN`, `526 VALIDATION`, `199 HOLDOUT` through 2026-07-16),
with only current-refresh deltas allowed. Fail closed if total selected dates
are outside `1,200..1,500`, any partition is absent, dates are duplicated or
unsorted, or any outcome field/call is observed.

## Frozen free-quote and acquisition geometry

- Databento dataset/schema/symbol: `GLBX.MDP3` / `mbp-10` / `6E.v.0`
- `stype_in=continuous`, `stype_out=instrument_id` for download.
- Each selected date: `[14:14:45,14:15:00) Europe/Berlin`, converted to UTC
  with IANA DST; exactly 15 seconds.
- The 15-second floor is a pre-outcome cost design chosen only because the
  Owner doubled the horizon while capping total spend at USD 2.25. It is the
  shortest allowed window; V2 must not shrink it further to force a quote
  under budget.
- Quote stage allowlist: `metadata.get_cost` and
  `metadata.get_billable_size` only.
- Paid stage: live re-quote all exact windows first; only then serial
  `timeseries.get_range` calls with an in-flight journal, exclusive outputs,
  full DBN decode, record count and SHA256 per response.
- Runtime: `02. AlphaFactory/runtime/python-databento/Scripts/python.exe`,
  `databento==0.54.0`; all source data stays under `02. AlphaFactory/data/`.

The source stage is not an EBS cash-spot test. CME 6E is a listed-futures
proxy. Source acquisition does not authorize economics, MQL5, Model 0,
optimization, promotion, paper or live trading.

## Next gate after download

An outcome-blind decoder must first prove exact coverage, sequence integrity,
usable depth/flow fields, non-crossed book states and a causally computable OFI
feature at `14:15`. Only a passing source-quality packet may support a fresh,
SHA-bound TRAIN economic preregistration. No source-quality result can be used
to tune the 15-second window or date-selection rule under this ID.
