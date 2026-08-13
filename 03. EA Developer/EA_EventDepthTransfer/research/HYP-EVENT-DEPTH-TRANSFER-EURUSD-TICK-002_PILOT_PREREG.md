# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-002 — source-pilot preregistration

Status: frozen after free metadata quote and before source payload access.

## Revision boundary

Parent `HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-001` made zero paid calls and read zero
source records because the live USD 0.013034924865 quote exceeded its USD 0.01 cap.
This child changes only acquisition mechanics:

- the half-open source window ends at T+60 seconds instead of T+120 seconds because
  the frozen formula consumes no information at or after T+60;
- the hard ceiling becomes USD 0.02 under the Owner's standing authorization for
  research spend below USD 10.

The vendor quoted the same USD 0.013034924865 and 27,992,288 billable bytes for the
minimum 60-second interval, consistent with source billing granularity. No payload,
return, target price, or economic result was read when making this revision.

## Exact source contract

- Pilot ID: `EVENTDEPTHTRANSFER002-MBP10-PILOT-001`
- Dataset/schema: `GLBX.MDP3` / `mbp-10`
- Symbol/stype: `6E.v.0` / `continuous`, output as `instrument_id`
- Clock/window: `ts_recv`, `[2019-01-03T15:00:00.000Z,2019-01-03T15:01:00.000Z)`
- At most one paid `timeseries.get_range`; no batch, subscription, or retry.
- Hard live quote ceiling: USD 0.02. A higher quote aborts before acquisition.
- Exclusive output root; a pre-existing root means the attempt is consumed.

## Frozen source formula

The formula is identical to the parent. For zero-based levels `n=1..9` only:

`Dbid = sum((10-n) * bid_sz[n])`; `Dask = sum((10-n) * ask_sz[n])`.

`Dbid0/Dask0` are the last valid snapshot at or before T+15. `Dbid1/Dask1` are
receive-time-weighted means on `[T+15,T+60)`, with valid coverage at least 99%.
Initial aggressor sign on `[T,T+15)` is `+1` for greater `T/B` volume, `-1` for
greater `T/A`, otherwise FLAT. At T+60:

`score = s * ((Dbid1-Dbid0)/Dbid0 - (Dask1-Dask0)/Dask0)`.

Positive is continuation in direction `s`; negative is reversal in direction `-s`;
zero is FLAT. Level 0 never contributes to the score.

## Integrity and authority

Require DBNv3 metadata match, one instrument ID, half-open containment, monotone
`ts_recv`, valid ten-level baseline, at least 99% valid interval coverage, no locked or
crossed state longer than 50 ms, nonzero initial aggressor imbalance, and SHA-256-bound
raw/receipts. This is source semantics only: no EURUSD outcomes, returns, economics,
MQL5, MT5, DESIGN population, validation, holdout, paper, promotion, or live authority.

