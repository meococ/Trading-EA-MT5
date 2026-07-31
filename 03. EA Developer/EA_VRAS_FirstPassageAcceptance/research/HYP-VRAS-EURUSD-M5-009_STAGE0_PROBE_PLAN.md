# HYP-VRAS-EURUSD-M5-009 — Frozen Stage-0 First-Passage Acceptance Probe

Status: **FROZEN PRE-PROBE / PRE-SOURCE / PRE-ECONOMIC-OUTCOME**  
Frozen: 2026-07-22 UTC  
Parent evidence: terminal `HYP-VRAS-EURUSD-M5-008` (mechanism inspiration only; no rescue authority)  
Proposed EA package if and only if Stage-0 passes: `EA_VRAS_FirstPassageAcceptance`

## Question

Can a categorical, closed-bar first-passage state machine create a materially different and operationally feasible entry decision surface from both:

1. HYP008's immediate same-bar rolling-VWAP reclaim + previous-extreme break; and
2. HYP004's fixed next-bar continuation confirmation?

Stage-0 measures only event identity, state transitions and cadence. It must not load, calculate, join, display or persist trade outcome, future return, excursion, SL/TP, win rate, P/L, PF, expectancy or drawdown.

## Why this is a legal new mechanism

Grok's validated random-100 synthesis ranks absent entry edge as the primary HYP008 failure and proposes a new sealed M5 path-quality information/state contract. A generic score, entropy threshold, extra M15 filter or `N`-bar delay would be outcome-contaminated and too close to terminal HYP004. HYP009 instead freezes a categorical first-passage FSM with no tunable acceptance threshold.

The mechanism is new only if the probe proves decision-identity divergence and viable cadence. Failure closes this candidate before MQL5/Model-0. HYP008 remains terminal regardless of result.

## Bound inputs

- EURUSD M1 closed bid bars: `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`, SHA256 `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- EURUSD H1 closed bid bars: `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_H1_2015_now.parquet`, SHA256 `71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08`.
- Canonical server clock: `02. AlphaFactory/tools/research/fivepercent_server_clock.py`, SHA256 `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.
- HYP008 source truth: SHA256 `720D45505282123D4C8B78428B9913F6ADD41176013E5B968A60C56CF446E53C`.
- Validated Grok synthesis packet: `.context/vras-hyp008-grok-random100/validated/synthesis.json`, SHA256 `1D682FDD77A74AAA91ECD16E2EE5149D3C9A12AF20AB71431E09CF1D4C1BF0A4`.
- Published Grok report: SHA256 `16630AD6BDFBA9CA891DE276D38217B0EAE2DD668A092726610C9EDF72A97AA9`; QC SHA256 `8F2FCFD3EEFD865A2008977ECCB2F0AE6A0A450AAC34745E6FC0A8331793DE02`.
- HYP004 terminal readout: SHA256 `D626C1A20F3985E4BC6FC0BC603BC3FB2D563765643139B590D48554CE6F337C`.

Discovery/identity window: `2019-01-01 00:00:00` through `2022-12-31 23:59:59` broker-server request, with exact first/last usable bars reported. Full 2015 history is used only as indicator warm-up. UTC is derived only through the bound clock model.

## Frozen indicator surface

- Resample M1 server bars to closed M5 OHLC + summed tick volume using left-labeled, left-closed 5-minute buckets. Incomplete/non-contiguous buckets fail closed.
- Rolling VWAP48 at completed M5 bar `t`: tick-volume-weighted typical price `(high+low+close)/3` over completed bars `t-47..t`. Zero total volume is invalid.
- H1 bias at M5 decision close: last fully closed H1 close and EMA200 available at that time. EMA200 is computed from the full bound 2015 history; no short warm-up.
- Long/short rules are exact mirrors. No ADX, RSI, M15, AVWAP, SD band, tick-volume threshold, distance score, entropy score, news filter or parameter grid.

## Frozen FSM

Only one candidate may be active. Every action uses completed bars.

### WAIT → RECLAIM

During `[07:00, 16:30)` canonical UTC:

- Long direction requires closed H1 close > closed H1 EMA200; short requires `<`.
- Long reclaim at completed M5 `t`: previous completed close `<= L`, current low `<= L`, and current close `> L`, where `L` is VWAP48 at `t`.
- Short mirror: previous close `>= L`, current high `>= L`, current close `< L`.
- Freeze origin ID/time, direction, `L`, reclaim high/low and H1 direction. A reclaim arms state only; it never enters.

### RECLAIM → HOLD

The immediately next contiguous completed M5 bar must:

- close on the accepted side of frozen `L`; and
- retain the same closed-H1 bias.

It cannot enter even if it breaks the reclaim extreme. Failure invalidates the candidate. On pass, freeze pair extreme `E=max(reclaim high, hold high)` for long or `min(reclaim low, hold low)` for short.

### HOLD → FIRST_PASSAGE resolution

Starting with the following contiguous completed M5 bar, evaluate in this order:

1. Session end, data gap/restart or H1-bias flip → reject/expire.
2. First close back through frozen `L` (`<=L` long, `>=L` short) → invalidate.
3. First close beyond frozen pair extreme `E` (`>E` long, `<E` short) → accept at that bar's close; a future EA would enter no earlier than the next tick/bar after the closed decision.
4. Otherwise remain pending.

The candidate expires when 48 completed M5 bars have elapsed from the reclaim origin, or at `16:30` UTC, whichever occurs first. `48` is inherited from the frozen VWAP information window, not selected from outcome. No `N`, ATR distance, body/wick, persistence, volume or score threshold exists.

Any non-contiguous M5 data, duplicated timestamp, indicator invalidity or clock ambiguity resets state and is counted. No state crosses a UTC day/session or weekend.

## Frozen comparators

All identity comparisons use the same raw reclaim origin IDs, not shifted entry timestamps.

- `HYP008_IMMEDIATE`: raw reclaim plus same completed bar breaking the previous completed M5 high/low.
- `ONE_BAR_CONFIRM`: raw reclaim whose immediately next completed bar holds frozen `L`, retains H1 bias and closes beyond the reclaim-bar high/low. This is a structural comparator, not a replay or economic result for HYP004.

## Stage-0 outputs and gates

Required outputs:

- exact data coverage/hashes and outcome-blind attestation;
- counts for raw reclaim, HOLD pass/fail, first-passage accept, VWAP recross invalidation, H1 flip, session expiry, 48-bar expiry and data-gap reset;
- accepted-event cadence per elapsed calendar week pooled and separately for 2019, 2020, 2021 and 2022;
- direction counts, decision-lag distribution and origin-ID overlap/Jaccard against both comparators;
- deterministic event ledger containing only decision-time state fields.

All necessary gates must pass:

1. no outcome source/field/path imported and no forward bar after each decision used;
2. deterministic rerun produces byte-identical event ledger;
3. indicator reconstruction parity on the frozen HYP008 random-100 accepted-entry telemetry: 100/100 direction/gate pass and absolute deltas for H1 close, H1 EMA200, VWAP48 and ATR14 `<=5.1e-6` (telemetry is rounded to five decimals);
4. total accepted events `>=350`;
5. accepted cadence is `>=2.00` and `<=5.00` per elapsed calendar week pooled and in every discovery year;
6. both directions have at least 50 accepted events;
7. origin-ID Jaccard is `<=0.80` versus `HYP008_IMMEDIATE` and `<=0.80` versus `ONE_BAR_CONFIRM`;
8. at least 20% of accepted events resolve three or more completed bars after reclaim, proving the surface is not merely a fixed two-bar rewrite.

If any gate fails: `PARK_STAGE0_IDENTITY_OR_CADENCE_FAIL`; no MQL5 source, compile or Model-0 is authorized. No threshold, session, expiry or comparator may be amended after counts.

## Conditional economic boundary if Stage-0 passes

Stage-0 PASS authorizes a separate frozen economic preregistration, red-first tests and a new canonical package. It does not itself authorize a backtest.

The future matched control/challenger must use one source/binary and differ only by the acceptance FSM. Common execution/risk must include the same session/overnight/weekend safety, stop/TP/BE and cost contract in both arms. Tester-only account-DD entry halt may be disabled to remove censorship, while live/default DD protection stays enabled; raw tester DD plus USD, R-unit and canonical-risk-normalized DD must all be reported.

Requested economic window is `2018-01-01` through an exact no-outcome last-closed-bar readback on the research date. Required slices are predeclared: 2018 stress; 2019–2022 discovery-tainted diagnostic; 2023–as-of primary OOS; and full horizon. One sealed matched pair is the only historical economic attempt for this successor. Failure means VRAS price-only reclaim frontier stop or forward-only collection, not another sibling threshold iteration.

