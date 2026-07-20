# HYP-ICT-FVG-HUMAN-CONTEXT-ENGINE-EURUSD-M5-015 - frozen decision-time Human Context Engine

Status: **FROZEN BEFORE SOURCE CHANGE, ENGINE OUTPUT OR CHILD OUTCOME**

Epistemic class: **NEW INFORMATION ENGINE DERIVED FROM OUTCOME-DISCLOSED
FORENSICS; ENGINEERING/COVERAGE ONLY, NOT AN ALPHA CLAIM**.

## Parent boundary

- Canonical parent engineering source: HYP-013 v1.19, SHA-256
  `1E04144A5E26651B993E7A13202FC85B8D5C0AB3FD7C8FAA5D890897E3B4B196`.
- HYP-012 and HYP-014 remain terminal. HYP-014's 12 features plus four
  interactions cannot be tuned, relaxed or rerun.
- The six HYP-014 anatomy charts are outcome-disclosed. Their H1-range-location
  lead authorizes construction of a new information engine, not a trading rule.

## Human Context Engine schema

At each candidate decision, before `TryOpenTrade`, build one immutable snapshot
from data available at that cutoff. The engine must expose, not optimize:

1. **Dealing range:** closed H1 and H4 20-bar high/low, raw entry location
   `(entry-low)/(high-low)`, and whether entry extends beyond the directional
   edge (long above high or short below low).
2. **Confirmed structure:** two latest confirmed pivot highs and lows on closed
   H1 and H4 bars, pivot strength 2 / lookback 120; classify bullish,
   bearish or mixed, then express alignment relative to trade direction.
3. **External liquidity map:** previous broker D1 high/low, previous broker W1
   high/low, current UTC Asia 00:00-07:00 high/low from closed M5 bars, latest
   confirmed H1 pivot and latest confirmed H4 pivot.
4. **Draw on liquidity:** nearest still-ahead directional pool, pool type,
   distance in pips, distance in initial R, number of ahead pools, and whether
   nearest room reaches the unchanged fixed `InpTargetRR`.
5. **Sweep taxonomy:** compare the observed sweep high/low/close with the
   decision-time external map; classify internal or external reclaim and count
   reclaimed external pools.
6. **Point-in-time partial HTF:** construct current H1 and H4 partial candle
   exclusively from M5 bars already closed by the decision cutoff. Record
   direction-normalized partial body / closed-HTF ATR. Never read H1/H4 bar 0.
7. **Initiation/exhaustion context:** confirmation body / closed M5 ATR,
   consecutive directional closed-M5 run length, H1/H4 directional range
   extension / ATR, and spread-to-risk ratio.
8. **Semantic state:** `INCOMPLETE`, `NO_DIRECTIONAL_TARGET`,
   `DIRECTIONAL_EXHAUSTION`, `STRUCTURE_CONFLICT`,
   `EXTERNAL_SWEEP_WITH_ROOM`, `INTERNAL_SWEEP_WITH_ROOM`, or
   `INSUFFICIENT_ROOM`. Natural boundaries only: range edge `0/1`, fixed
   target RR, existence of a directional pool and categorical structure. No
   learned score or fitted threshold.

Frozen engine inputs: H1/H4 range bars `20`, pivot strength `2`, pivot lookback
`120`, ATR period `14`, Asia window `00:00-07:00 UTC`. They are engineering
definitions in this child and cannot be varied using output.

## Source and telemetry contract

- Add a package-local `HumanContextEngine.mqh` and embed HYP-015 / v1.20 in the
  canonical EA. Main signal, sessions, news, stop, target, break-even, risk,
  Friday safety and order lifecycle remain byte-semantically unchanged.
- Create a separate decision-event CSV. It must be written before trade send,
  contain no exit/PnL/MFE/MAE/future-bar field, and log valid plus incomplete
  snapshots for control, context-state and full-fidelity entry decisions.
- Engine state is observation-only in HYP-015: it cannot reject, resize, move a
  stop/target or change a signal.

## Red-first and no-lookahead proof

- Contract tests must fail against HYP-013 and prove the exact schema, separate
  telemetry surface, pre-send call ordering, no outcome fields and unchanged
  parent signal geometry.
- Every H1/H4/D1/W1 `CopyRates` read starts at shift 1. Partial H1/H4 uses only
  closed M5 (`CopyRates(...PERIOD_M5,1,...)`) bounded by decision time.
- AlphaFactory compile, exact-source non-repaint audit and a fresh
  source/dependency/binary/compile-log receipt are mandatory.

## Offline reference and frozen coverage gates

- Reference input is the hash-bound HYP-012 entry ledger SHA
  `1661ECE4...B5B6` plus M5 parquet SHA `AAF14451...21C73`.
- The reference builder is forbidden to read `r_gross`, `r_net`, exit, PnL,
  commission or later bars. It must produce all 3,385 decision rows.
- Required before any policy child:
  - >=99% complete context snapshots;
  - all six HYP-014 case H1 range-location values match the existing
    `chart_case_render.v2` manifest within `1e-9`;
  - zero future-cutoff violations, zero duplicate identities;
  - exact repeat hashes for feature CSV and coverage result.

Failure ends HYP-015 as `PARKED_ENGINE_INCOMPLETE_NO_POLICY`. Passing parks the
engine as engineering-complete and only permits a fresh HYP-016 plan. HYP-015
has no economic run, source gating, Model-0, paper/live or promotion authority.

