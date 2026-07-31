# HYP-VRAS-EURUSD-M5-011 — Frozen Stage-0 First-Passage Acceptance Probe

Status: **FROZEN PRE-IMPLEMENTATION / PRE-PROBE / PRE-SOURCE / PRE-ECONOMIC-OUTCOME**  
Frozen: 2026-07-23 UTC  
Package if and only if Stage-0 passes: `EA_VRAS_FirstPassageAcceptance`

## Identity and legal boundary

HYP011 carries the never-run first-passage mechanism from administrative parks
HYP009/HYP010 under a corrected single contract. Neither predecessor opened a
real probe, event count, cadence, overlap, P/L, return or excursion. HYP011 is
therefore not result-informed rescue.

The question is whether a categorical, closed-bar first-passage state machine
creates a materially different and operationally feasible entry-decision
surface from HYP008 immediate reclaim/break and a fixed one-bar confirmation.
Stage-0 measures identity, state transitions and cadence only. It may not load,
calculate, join, display or persist realized trade outcome, future return,
excursion, exit, P/L, PF, expectancy, balance, equity or drawdown.

## Exact bound inputs

- M1 closed bid bars:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`,
  SHA256 `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- H1 closed bid bars:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_H1_2015_now.parquet`,
  SHA256 `71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08`.
- Server clock:
  `02. AlphaFactory/tools/research/fivepercent_server_clock.py`,
  SHA256 `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.
- HYP008 decision telemetry, exact path (no wildcard/discovery):
  `02. AlphaFactory/runs/EA_VRAS_VolatilityNormalizedStop/20260722_233420/analysis/logs/EURUSD_DecisionTelemetry_HYP-VRAS-EURUSD-M5-008_188132734.csv`,
  SHA256 `C510692DB20D710D92FCDE52C8628B158D98AAFE00BD3211E5E36E74254EDF66`.

Discovery/identity window is broker-server request `2019-01-01 00:00:00`
through `2022-12-31 23:59:59`. Earlier history is indicator warm-up only. UTC
is derived only with the bound clock.

## Telemetry parser and parity

The exact telemetry header is:

`server_time,variant,status,direction,h1_close,h1_ema,rolling_vwap_48,atr14,entry,stop,target,spread_pips`

After exact SHA verification, the CSV parser may ephemerally parse a complete
row from this exact decision-time-only producer file, but the retained data
surface is restricted to:

`server_time,status,direction,h1_close,h1_ema,rolling_vwap_48,atr14`

`entry/stop/target/spread_pips` are planned decision-time geometry, not realized
outcomes; the probe must never use, retain, emit or compare them. Any missing,
reordered or extra header fails. Every other path/schema containing lifecycle,
report, casebook, random sample, anatomy, exit, outcome, profit, return, MFE,
MAE, balance, equity or deal is forbidden.

Parity sample is the first 100 `ORDER_ACCEPTED` rows sorted by parsed server
time, then direction, preserving stable file order for ties. The exact bound
producer timestamps are required to have zero seconds/microseconds and minute
divisible by five; otherwise fail rather than infer a bar. Reconstructed and
telemetry direction/H1 close/H1 EMA200/VWAP48/ATR14 must all be finite. Required
parity is 100/100 direction and absolute numeric deltas `<=5.1e-6`.

## Frozen indicator and gap surface

- M1 timestamps must be unique and minute-aligned. A usable M5 bucket contains
  exactly offsets `00,01,02,03,04` inside its left-labelled five-minute bucket.
  Partial/duplicate/misaligned buckets are invalid, cannot seed the next
  reclaim, and poison rolling indicators until their required observed-bar
  lookback is clean.
- A completely absent five-minute interval is not an observed bar and is not
  inserted into rolling windows, matching MT5 `CopyRates` over actual broker
  bars (including scheduled weekend closure). It resets any active candidate;
  the first observed bar after the gap cannot arm because its predecessor is
  non-contiguous.
- VWAP48 at completed M5 `t` is tick-volume-weighted typical price over the
  last 48 valid observed completed bars. Zero total volume is invalid.
- H1 bias uses last fully closed H1 close and EMA200, with full bound warm-up.
- ATR14 is simple mean true range matching the parity-proven MT5 iATR semantics
  in this workspace and is used only for parity, never by the FSM.
- Long/short rules mirror. No ADX, RSI, M15, AVWAP, SD band, volume/entropy/
  distance/body/wick threshold, news filter or grid.

## Frozen state machine

Only one candidate may be active. All actions use completed bars in session
`[07:00,16:30)` canonical UTC.

### WAIT → RECLAIM

- Long requires closed H1 close above EMA200; short requires below.
- Long at completed M5 `t`: previous completed close `<=L`, current low `<=L`,
  current close `>L`, where `L=VWAP48(t)`. Short mirrors.
- Freeze origin ID/time, direction, `L`, reclaim high/low and H1 direction.
  Reclaim arms only and cannot enter.

### RECLAIM → HOLD

The immediately next contiguous completed M5 bar must remain in session and
same UTC day, retain H1 bias and close on the accepted side of frozen `L`. It
cannot enter. Failure invalidates. Pass freezes pair extreme
`E=max(reclaim high,hold high)` long or mirrored min short.

### HOLD → FIRST_PASSAGE

Starting from the following contiguous completed M5 bar, evaluate in order:

1. invalid data/gap, session/day expiry or H1 flip → reject;
2. 48 completed M5 bars elapsed from origin → expire;
3. first close back through frozen `L` → invalidate;
4. first close beyond frozen `E` → accept at that bar close;
5. otherwise remain pending.

No state crosses a UTC session/day/weekend. A resolving bar may arm a new raw
candidate only after the old state is closed.

## Frozen comparators

All identity comparisons use armed raw-reclaim origin IDs.

- `HYP008_IMMEDIATE`: reclaim bar also closes beyond previous M5 high/low.
- `ONE_BAR_CONFIRM`: actual contiguous HOLD bar retains bias/`L` and closes
  beyond reclaim high/low.

The one-bar comparator is evaluated only when the HOLD bar is processed. No
`t+1` row is indexed while handling the origin.

## Necessary Stage-0 gates

Outputs are a deterministic decision-state event ledger and summary with exact
hashes/coverage; raw/HOLD/accept/invalidation/expiry/gap counts; elapsed-week
cadence pooled and by 2019–2022 year; direction counts; lag distribution; and
origin Jaccard. HYP011 schema identifiers are mandatory.

All gates must pass:

1. exact plan/data/clock/telemetry hashes, exact path/header and retained-field
   allowlist;
2. an internal second FSM run emits byte-identical event-ledger bytes;
3. finite indicator parity 100/100 within `5.1e-6`;
4. accepted events `>=350`;
5. cadence `2.00..5.00` per elapsed calendar week pooled and every year;
6. at least 50 accepted events each direction;
7. origin Jaccard `<=0.80` against both comparators;
8. at least 20% accepted decisions resolve at lag `>=3` bars.

Any failure yields `PARK_STAGE0_IDENTITY_OR_CADENCE_FAIL`, with no MQL5,
compile, Model-0 or threshold/session/rule amendment.

## Conditional economic boundary

Only complete Stage-0 PASS permits a separate preregistered matched economic
test. One source/binary must differ only by control/challenger acceptance FSM,
Model 0 must span `2018-01-01` to an exact live readback of the last closed bar,
and slices are 2018 stress, 2019–2022 discovery-tainted, 2023–as-of primary OOS
and full horizon. Tester-only account-DD entry halt may be disabled so history
is uncensored; live/default protection remains enabled and DD remains measured
raw plus risk-normalized.

Only one sealed historical economic successor is allowed. Failure means a
VRAS price-only reclaim frontier stop or forward-only collection, not another
parameter sibling.
