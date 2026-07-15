# Sonic R Preregistration Template

Use this before any meaningful backtest or EA rule patch.

## Identity

- Hypothesis ID:
- Parent candidate:
- Author/session:
- Date:
- State on creation: `idea`

## Thesis

- Trader/market thesis:
- Source provenance: public source / reconstructed mapping / local empirical / hypothesis
- Feature family:
- Lane/setup:
- Symbol/timeframe:
- Market regime expected:
- Why this is independent from existing XAU 2024-2025 pocket:

## Locked Design

- Exact feature definition:
- Closed-bar decision timestamp and first executable entry tick (never the same
  historical close used by the signal):
- UTC half-open bucket/window definition and tick sort/tie/aggregation rule:
- Bid/ask side used for every entry, stop, target, and time exit:
- Episode start, overlap arbitration, arm expiry, cooldown, and reset rule:
- Missing quote/cost policy (whole split fails; no eligible-episode deletion):
- PF formula and zero-trade/zero-loss/non-finite fail-closed policy:
- Maximum tunable parameters:
- Frozen parameter/search space:
- Banned post-result edits:
- Allowed edits before first run:
- Expected affected bars/trades before backtest:
- Negative controls:

## Chart-State Label Contract

Required labels before EA rule patch:

- Wave state: clean / choppy / overlap / unclear
- Dragon state: flat / compressed / expanding / angled
- Trend/HTF state: aligned / soft conflict / hard conflict / unknown
- S/R runway: clear / blocked / near whole-half-quarter / unknown
- Chase risk: early / mature / late chase / unknown
- Trap/build vs run-for-profits: build / run / trap risk / unknown
- Session phase:
- Invalidation:
- Required MT5-native snapshot cases:

## Test Plan

- Baseline/control:
- Model 1 screen command:
- Model 0 confirmation command:
- Telemetry tier: off / trade-only / state-lite / state-full / snapshot-casebook
- Date windows:
- Separate train and untouched holdout gates:
- Cost stress x1/x1.5/x2:
- Commission evidence (30 lifecycles or hash-pinned account/symbol contract):
- Slippage evidence (100 side-referenced fills, at least 30 buy and 30 sell):
- Per-trade account-currency/pip conversion rule and source hash:
- Validation gates:
- Run budget:
- Kill criteria:
- Park criteria:
- Promotion criteria:

## Preflight Checklist

- Canonical source path confirmed:
- Source hash:
- Compiled artifact timestamp/hash:
- Git status snapshot:
- Symbol suffix confirmed:
- Model/dates/overrides confirmed:
- MT5 runtime/terminal path:
- Common Files sidecar destination clean:
- Existing stale tester processes reviewed:

## Expected Outcome

- Expected improvement:
- Expected failure mode:
- What result would falsify the idea:
