# HYP-VRAS-EURUSD-M5-010 — Frozen Stage-0 First-Passage Acceptance Probe

Status: **FROZEN PRE-IMPLEMENTATION / PRE-PROBE / PRE-SOURCE / PRE-ECONOMIC-OUTCOME**  
Frozen: 2026-07-23 UTC  
Package if and only if Stage-0 passes: `EA_VRAS_FirstPassageAcceptance`

## Identity and legal boundary

HYP010 carries forward the never-run first-passage mechanism from HYP009 under
one internally consistent contract. HYP009 was parked before any count or
outcome because its V2 telemetry clause was impossible to execute. HYP010 is
not a result-informed rescue: Stage-0 event count, cadence, overlap, P/L,
forward return and excursion remain unopened.

The question is whether a categorical, closed-bar first-passage state machine
creates a materially different and operationally feasible entry-decision
surface from both HYP008's immediate reclaim/break and a fixed one-bar
confirmation. Stage-0 measures identity, state transitions and cadence only.
It must never load, calculate, join, display or persist trade outcome, future
return, excursion, realized entry/exit, P/L, PF, expectancy or drawdown.

## Bound inputs

- EURUSD M1 closed bid bars:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`,
  SHA256 `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- EURUSD H1 closed bid bars:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_H1_2015_now.parquet`,
  SHA256 `71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08`.
- Canonical server clock:
  `02. AlphaFactory/tools/research/fivepercent_server_clock.py`,
  SHA256 `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.
- HYP008 challenger decision telemetry:
  `02. AlphaFactory/runs/EA_VRAS_VolatilityNormalizedStop/20260722_233420/analysis/logs/EURUSD_DecisionTelemetry_HYP-VRAS-EURUSD-M5-008.csv`,
  SHA256 `C510692DB20D710D92FCDE52C8628B158D98AAFE00BD3211E5E36E74254EDF66`.

Discovery/identity window is broker-server request `2019-01-01 00:00:00`
through `2022-12-31 23:59:59`. Full earlier history is indicator warm-up only.
UTC is derived only with the bound clock model.

## Outcome-blind telemetry projection

The exact telemetry file has this fixed header:

`server_time,variant,status,direction,h1_close,h1_ema,rolling_vwap_48,atr14,entry,stop,target,spread_pips`

After verifying the exact file SHA, the probe must require that exact ordered
header and stream-project only:

`server_time,status,direction,h1_close,h1_ema,rolling_vwap_48,atr14`

It must never materialize, persist, compare or expose `entry`, `stop`, `target`
or `spread_pips`. Any missing, reordered or extra column fails closed; every
other path/schema containing lifecycle, report, casebook, random sample,
anatomy, exit, outcome, net, P/L, return, MFE, MAE, balance, equity or deal is
forbidden.

Parity sample is the first 100 `ORDER_ACCEPTED` rows sorted by parsed broker
server time, then direction, preserving stable file order for exact ties.
Required parity is 100/100 direction plus absolute deltas for H1 close, H1
EMA200, VWAP48 and ATR14 `<=5.1e-6`.

## Frozen indicator surface

- Resample M1 to left-labelled/left-closed completed M5 OHLC and summed tick
  volume. Duplicate timestamps fail. An incomplete M1 bucket is not usable and
  cannot seed the next reclaim; rolling indicator values that include it fail
  closed until their lookback is clean.
- VWAP48 at completed M5 bar `t` is the tick-volume-weighted typical price
  `(high+low+close)/3` over completed bars `t-47..t`; zero volume is invalid.
- H1 bias at M5 close uses the last fully closed H1 close and EMA200, with the
  EMA computed from full bound warm-up history.
- ATR14 exists only for parity. The FSM does not use ATR.
- Long/short rules are exact mirrors. No ADX, RSI, M15, AVWAP, SD band,
  volume threshold, entropy/distance/body/wick score, news filter or grid.

## Frozen state machine

Only one candidate may be active. All actions use completed bars. Session is
`[07:00,16:30)` canonical UTC.

### WAIT → RECLAIM

- Long requires closed H1 close above closed H1 EMA200. Short requires below.
- Long at M5 `t`: previous completed close `<=L`, current low `<=L`, current
  close `>L`, where `L=VWAP48(t)`. Short is the exact mirror.
- Freeze origin ID/time, direction, `L`, reclaim high/low and H1 direction.
  Reclaim only arms state; it cannot enter.

### RECLAIM → HOLD

The immediately next contiguous completed M5 bar must close on the accepted
side of frozen `L`, retain the same closed-H1 bias, remain in session and on
the same UTC day. It cannot enter. Failure invalidates the candidate. On pass,
freeze pair extreme `E=max(reclaim high,hold high)` long or the mirrored min.

### HOLD → FIRST_PASSAGE

Starting with the following contiguous completed M5 bar, evaluate in order:

1. data invalidity/gap, session/day expiry or H1-bias flip → reject;
2. 48 completed M5 bars elapsed from origin → expire;
3. first close back through frozen `L` → invalidate;
4. first close beyond frozen `E` → accept at that bar's close;
5. otherwise remain pending.

No state crosses a UTC day/session/weekend. A resolving bar may arm a new raw
candidate only after the old state is closed; never more than one remains
active.

## Frozen comparators

Identity uses raw reclaim origin IDs, not shifted decision times.

- `HYP008_IMMEDIATE`: armed raw reclaim whose reclaim bar also closes beyond
  the previous completed M5 high/low.
- `ONE_BAR_CONFIRM`: armed raw reclaim whose actual contiguous HOLD bar retains
  H1 bias, holds frozen `L` and closes beyond reclaim high/low.

The one-bar comparator is evaluated only when that HOLD bar is processed. The
implementation may not index or inspect `t+1` while handling the origin.

## Required outputs and necessary gates

The deterministic event ledger contains decision-state fields only. Summary
must report exact hashes/coverage, raw/HOLD/accept/invalidation/expiry/gap
counts, cadence per elapsed calendar week pooled and for each 2019–2022 year,
direction counts, lag distribution and origin Jaccard.

All gates must pass:

1. exact contract/data/clock/telemetry hashes and allow-list projection;
2. internal second FSM run emits byte-identical event-ledger bytes;
3. indicator parity 100/100 within `5.1e-6`;
4. accepted events `>=350`;
5. cadence `2.00..5.00` per elapsed calendar week pooled and every year;
6. at least 50 accepted events in each direction;
7. Jaccard `<=0.80` against both comparators;
8. at least 20% of accepted decisions resolve at lag `>=3` bars.

Any failure yields `PARK_STAGE0_IDENTITY_OR_CADENCE_FAIL`. It authorizes no
MQL5 source, compile or Model-0 and no rule/threshold/session amendment.

## Conditional economic boundary

Only a complete Stage-0 PASS permits a separate preregistered matched economic
test. It must use one source/binary with control/challenger differing only in
the acceptance FSM, run Model 0 from `2018-01-01` to an exact live readback of
the last closed bar, and report 2018 stress, 2019–2022 discovery-tainted,
2023–as-of primary OOS and full-horizon slices. Tester-only account-DD entry
halt may be disabled so the history is uncensored, while live/default DD
protection remains enabled and raw plus normalized DD remains measured.

Only one sealed historical economic successor is allowed. Failure means a
VRAS price-only reclaim frontier stop or forward-only collection, not another
parameter sibling.
