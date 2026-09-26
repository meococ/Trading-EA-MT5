# FROZEN PREREG — HYP-LSWEEP-XAU-M5-001

Frozen before any Strategy Tester outcome for this hypothesis. 2026-09-17.
Sibling document: `research/CONTRACT.md` (same directory) is the human contract
(frozen 2026-08-31); this file is the registry-bound preregistration for the
XAUUSD sleeve — the second hypothesis ID already declared in that contract.

## Delta vs killed neighbors (declared up front)

- `HYP-LSWEEP-EUR-M5-001` (sibling sleeve, killed 2026-09-12): died on cadence
  (N=172 over 27y, ~0.1/wk) at PF 0.68 on EURUSD. This run does not rescue it —
  it is the contract's separate XAUUSD cell, where sweep density is expected to
  differ materially (ROUND levels every $5 vs $0.0050, larger M5 ATR).
- `HYP-SWEEPFADE-XAUUSD-H1-001` (killed 2026-08-16): closed-bar PDH/PDL-only
  fade on H1, no session windows, no round/opening-range/Asia levels, different
  exits. Radius was that H1 envelope — not this M5 multi-level session-window
  mechanism.
- `HYP-VWF-XAU-M5-001` / `HYP-HD-XAU-M15-001` (killed 2026-09-12): VWAP fade
  and hour-drift momentum — different mechanisms entirely, listed only to show
  this cell is not a rename of a dead probe.

## Hypothesis (frozen)

- **Mechanism:** Liquidity-sweep reversion (Osler 2003). Stop-loss orders
  cluster just beyond salient intraday reference levels; a bounded excursion
  beyond a level that closes back inside was a stop cascade absorbed by
  dealers, whose inventory unwind is the payoff. Trade AGAINST the sweep.
- **Reference levels (closed bars only):** prior completed D1 high/low;
  Asia 00:00-07:00 GMT range; session opening range (first InpOrBars=6 M5
  bars after London 07:00 / NY 12:00 GMT); round numbers at InpRoundStep
  = 5.0 for XAUUSD.
- **Sweep geometry:** penetration 0.15-1.00 x ATR(M5,14) beyond the level;
  confirmation bar closes back inside; approached from origin side;
  outside-bar ambiguity rejected; largest penetration wins ties.
- **Direction:** swept a high => short; swept a low => long.
- **Exits:** SL = sweep extreme +/- 0.45 x ATR, floored at 4x spread
  (broker-side); TP = 1.30R (broker-side); time stop 24 M5 bars;
  break-even at 0.70R; daily flat server >= 22; Friday flat >= 20.
- **Symbol / timeframe:** XAUUSD, M5 closed-bar decisions.
- **Sessions:** London + New York liquidity windows on the derived GMT
  clock (server offset +2 winter / +3 US DST); rollover hours 23/0 server
  excluded.
- **Sizing:** 0.35% equity risk per trade; margin-capped; max 6
  entries/day; daily loss lock 2%; account DD lock 10%; streak lock 4.
- **News:** +/-20 min high-impact blackout; tester calendar is empty by
  design (fail-open, counted via news_query_empty).
- **Decision semantics:** closed-bar only; stdlib iATR + native OHLC
  levels; no custom indicator. Execution via shared AF_ExecutionKernel.

## Environment (frozen)

- **Broker/server:** MetaQuotes Ltd. / MetaQuotes-Demo (AlphaFactory portable
  isolate `mt5-portable-mqdemo`). RESEARCH-ONLY, non-promotable.
- **Coverage mode:** `all_available_asof` — From=1970.01.01 sentinel resolving
  to first real XAUUSD history 2004.06.11, To=2026.09.10 (pinned to the proven
  window of the killed XAUUSD runs HYP-VWF/HD/GBB-S3 so the data fingerprint
  98% / 1,493,135 bars / 523,708,245 ticks reproduces exactly).
- **Model:** 0 (every tick generated from M1 bars; not broker real ticks).
- **Cost tier:** `research_proxy`. Spread = tester `current` (measured XAUUSD
  window). Commission = conservative bound $7.00/lot RT over real same-symbol
  lifecycles. Slippage = independent-quote measured proxy @250ms.
- **Clock open item:** the first journal `LSW_CLOCK_DIAG` line must show
  `gmt_minus_server_sec` consistent with offset +2 (winter) for
  MetaQuotes-Demo; if not, pinning the offset is an engineering fix that
  does not consume market-revision budget.

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

Baseline + at most 2 market-logic revisions, then KILL. No year/hour/day/
subgroup salvage. No OOS/holdout reads before configuration freeze.

## Kill criteria (frozen)

- Gross result <= 0 after modeled costs, or cadence < 10 trades/week.
- Engineering invalidity that cannot be repaired without changing the frozen
  signal semantics (that repair becomes a new hypothesis row).

## Non-goals

- No promotion, no demo deployment, no live inference from this packet.
- No pooled P&L with the sibling EUR sleeve; XAUUSD stands alone.
