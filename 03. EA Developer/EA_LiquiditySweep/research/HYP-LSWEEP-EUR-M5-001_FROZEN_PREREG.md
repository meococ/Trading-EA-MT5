# FROZEN PREREG — HYP-LSWEEP-EUR-M5-001

Frozen before any Strategy Tester outcome for this hypothesis. 2026-09-12.
Sibling document: `research/CONTRACT.md` (same directory) is the human contract
(frozen 2026-08-31); this file is the registry-bound preregistration for the
EURUSD sleeve.

## Hypothesis (frozen)

- **Mechanism:** Liquidity-sweep reversion (Osler 2003). Stop-loss orders
  cluster just beyond salient intraday reference levels; a bounded excursion
  beyond a level that closes back inside was a stop cascade absorbed by
  dealers, whose inventory unwind is the payoff. Trade AGAINST the sweep.
- **Reference levels (closed bars only):** prior completed D1 high/low;
  Asia 00:00-07:00 GMT range; session opening range (first InpOrBars=6 M5
  bars after London 07:00 / NY 12:00 GMT); round numbers at InpRoundStep
  = 0.0050 for EURUSD.
- **Sweep geometry:** penetration 0.15-1.00 x ATR(M5,14) beyond the level;
  confirmation bar closes back inside; approached from origin side;
  outside-bar ambiguity rejected; largest penetration wins ties.
- **Direction:** swept a high => short; swept a low => long.
- **Exits:** SL = sweep extreme +/- 0.45 x ATR, floored at 4x spread
  (broker-side); TP = 1.30R (broker-side); time stop 24 M5 bars;
  break-even at 0.70R; daily flat server >= 22; Friday flat >= 20.
- **Symbol / timeframe:** EURUSD, M5 closed-bar decisions.
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
- **Coverage mode:** `verified_m1_asof` — From=1999.01.01 (first real-M1
  year on this broker; 1971-1998 are daily-stub .hcc), To=last closed
  server day. Precedent and gate semantics: see
  `04. Memory/research/20260912_IBSC_EURUSD_KILL_AND_VERIFIED_M1_MODE.md`.
- **Model:** 0 (every tick generated from M1 bars; not broker real ticks).
- **Cost tier:** `research_proxy`. Spread = tester `current` (measured
  EURUSD p90 0.1 pips). Commission = conservative bound $7.00/lot RT over
  real same-symbol lifecycles (broker observed 0). Slippage =
  independent-quote measured proxy @250ms.
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
- No pooled P&L with the sibling XAU sleeve; EURUSD stands alone.
