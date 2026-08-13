# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-001 — source-pilot preregistration

Status: frozen before source payload access.

## Market thesis

The L1 replenishment pilot proved that CME 6E trade and quote semantics are available,
but L1-only refill/depletion direction was arbitrary. This child does not revise that
mapping. It measures whether liquidity migrates asymmetrically through levels 2–10
after the initial event impulse. This is a materially different depth-transfer feature.

## Exact source contract

- Pilot ID: `EVENTDEPTHTRANSFER001-MBP10-PILOT-001`
- Dataset/schema: `GLBX.MDP3` / `mbp-10`
- Symbol/stype: `6E.v.0` / `continuous`, output as `instrument_id`
- Clock: `ts_recv`
- Half-open window: `[2019-01-03T15:00:00.000Z, 2019-01-03T15:02:00.000Z)`
- Event time T: `2019-01-03T15:00:00.000Z`
- One metadata cost call, one billable-size call, at most one paid
  `timeseries.get_range`; no batch, subscription, or automatic retry.
- Hard live quote ceiling: USD 0.01. A higher quote aborts before acquisition.
- Exclusive output root; a pre-existing root means the attempt is already consumed.

## Frozen source formula

For every valid 10-level snapshot, use zero-based levels `n=1..9` only. Level 0 is
excluded from the score. Weight level `n` by `10-n`:

`Dbid = sum((10-n) * bid_sz[n], n=1..9)`

`Dask = sum((10-n) * ask_sz[n], n=1..9)`

- `Dbid0`, `Dask0`: last valid snapshot at or before T+15 s.
- `Dbid1`, `Dask1`: receive-time-weighted means over `[T+15 s,T+60 s)`.
  A snapshot is held until the next `ts_recv`; the final state is held to T+60 s.
- Required valid coverage of that 45-second interval: at least 99%.
- Initial aggressor sign in `[T,T+15 s)`: `s=+1` when buyer-aggressor (`T/B`)
  volume exceeds seller-aggressor (`T/A`) volume; `s=-1` for the opposite; equality
  is `FLAT`.
- `score = s * ((Dbid1-Dbid0)/Dbid0 - (Dask1-Dask0)/Dask0)`.
- `score > 0`: `CONTINUATION`, direction `s`.
- `score < 0`: `REVERSAL`, direction `-s`.
- `score == 0`: `FLAT`.
- The decision is fixed at T+60 s. No threshold is tuned from this event.

## Integrity gates

- Non-empty DBNv3 Zstandard payload; metadata dataset/schema match.
- Exactly one observed instrument ID and all records are inside the half-open window.
- `ts_recv` is monotone.
- A valid baseline exists at or before T+15 s; valid snapshots contain ten levels,
  positive bid/ask prices and sizes, and an unlocked/uncrossed BBO.
- Weighted interval coverage is at least 99%.
- No continuously locked/crossed book state lasts more than 50 ms.
- Initial buyer/seller aggressor imbalance is nonzero.
- Raw payload and all receipts are SHA-256 bound.

The continuous-symbol resolution is bound through `stype_out=instrument_id`, the DBN
metadata, and the single observed instrument ID. A separate definition/status stream
is not requested because the one-call cap forbids mixing schemas.

## Authority boundary

This pilot may establish only source availability, field semantics, integrity, and one
classification for EVT0001. It may not access EURUSD outcomes, compute returns or PnL,
claim edge, create MQL5, open MT5, or authorize DESIGN/validation/holdout acquisition.
Any next stage requires a new frozen population/cost contract.

