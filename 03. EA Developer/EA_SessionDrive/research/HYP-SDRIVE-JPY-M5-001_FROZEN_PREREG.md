# FROZEN PREREG — HYP-SDRIVE-JPY-M5-001

Frozen before any Strategy Tester outcome for this hypothesis. 2026-09-18.
Sibling document: `research/CONTRACT.md` (same directory) is the human
contract (frozen 2026-09-18); this file is the registry-bound
preregistration for the USDJPY sleeve — the second hypothesis ID declared
in that contract. Frozen before any USDJPY tester outcome, including the
data-identity discovery run.

## Delta vs killed neighbors (declared up front)

- `HYP-SDRIVE-GBP-M5-001` (killed 2026-09-18, run 20260918_080056): the
  same mechanism on GBPUSD. Killed on BOTH frozen axes — cadence 0.199/wk
  under contract (account DD lock latched after first 10% drawdown and
  vetoed 68% of 21,099 signals permanently; spread filter vetoed 30%)
  and economics (287 trades, PF 0.778 gross / 0.717 cost-x1). This JPY
  cell is NOT a revision of GBP — it is the contract's second declared
  symbol sleeve, an independent falsification of whether ORB continuation
  has edge on USDJPY session structure (Tokyo/LDN/NY opens, different
  volatility/cost profile: JPY spread ~1pt on 3-digit quote, ATR profile
  differs). If JPY also shows PF <= ~0.8 gross on its executed sample,
  the mechanism family is falsified across both cost-viable FX symbols
  and no further SDRIVE cells are legal.
- `HYP-LSWEEP-EUR/XAU-M5-001` (killed): complementary direction, same
  cadence/economics death — see GBP prereg for the full delta.
- SilverBullet USDJPY (archived): the only JPY family with historical
  WFA pass (PF ~1.28-1.33), but ~2 tpw cadence (below band), The5ers
  transfer killed (PF ~1.02), and restore is gated on Owner action.
  SD-JPY is a different mechanism (simple ORB, not ICT KZ+FVG) targeting
  the cadence band; not a SilverBullet revival.

## Hypothesis (frozen)

- **Mechanism:** identical frozen semantics to HYP-SDRIVE-GBP-M5-001 —
  3-session (Asia 00-07 / London 07-16 / NY 12-20 GMT) opening-range
  breakout continuation, `or_bars=4` M5, close-beyond-extreme trigger,
  max 1 entry/session, break window 48 bars, OR validity [0.5,6.0]xATR14.
- **Exits:** SL = OR midpoint +/- 0.10 x ATR, floored at 4x spread;
  TP = 1.30R; time stop 24 M5 bars; break-even at 0.70R; daily flat
  server >= 22; Friday flat >= 20.
- **Symbol / timeframe:** USDJPY, M5 closed-bar decisions.
- **Sizing:** 0.35% equity risk; max 6 entries/day; daily loss lock 2%;
  account DD lock 10%; streak lock 4.
- **News:** +/-20 min high-impact blackout; fail-open counted.
- **Decision semantics:** closed-bar only; stdlib iATR; shared
  AF_ExecutionKernel. Same audited source bytes as the GBP cell
  (source hash pinned in the registry row).

## Environment (frozen)

- **Broker/server:** MetaQuotes Ltd. / MetaQuotes-Demo (AlphaFactory
  portable isolate `mt5-portable-mqdemo`, build 6198). RESEARCH-ONLY.
- **Coverage mode:** `verified_m1_asof` — From bound to the real M1
  coverage start discovered on the isolate (local .hcc currently covers
  2022+; tester will sync earlier server history if available; the
  packet binds whatever the discovery report proves), To=2026.09.11.
- **Model:** 0. **Cost tier:** `research_proxy` — USDJPY spread/slippage/
  commission evidence measured on the build-6198 isolate before the run.
- **Data-quality gate:** report History Quality > 97, unbypassed.

## Acceptance contract (frozen; matches registry row + task packet)

| Gate | Value |
|---|---|
| min_profit_factor | 1.30 |
| min_trades_per_week | 10.0 |
| max_trades_per_week | 40.0 |
| max_drawdown_pct | 20.0 |
| min_cost_pf_x1_5 | 1.25 |
| min_cost_pf_x2 | 1.0 |
| max_monte_carlo_p95_dd_pct | 20.0 |

## Trial budget (frozen)

Baseline + at most 2 market-logic revisions, then KILL. No subgroup
salvage. Dropping a session post-hoc is a new hypothesis.

## Kill criteria (frozen)

- Gross result <= 0 after modeled costs, or cadence < 10 trades/week.
- Engineering invalidity unrepairable without changing frozen semantics.
- Coverage insufficient for the confirmation gates AND not repairable by
  server-side history sync (declared up front: local M1 starts 2022;
  if MetaQuotes-Demo has no deeper JPY history the window is what it is —
  a short window can still KILL; it cannot PASS the confirmation gates,
  which is itself a kill on this data plane).

## Non-goals

- No promotion, no demo deployment, no live inference from this packet.
- No pooled P&L with the killed GBPUSD sleeve; USDJPY stands alone.
