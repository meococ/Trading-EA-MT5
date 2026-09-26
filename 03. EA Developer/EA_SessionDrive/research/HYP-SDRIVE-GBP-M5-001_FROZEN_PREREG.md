# FROZEN PREREG — HYP-SDRIVE-GBP-M5-001

Frozen before any Strategy Tester outcome for this hypothesis. 2026-09-18.
Sibling document: `research/CONTRACT.md` (same directory) is the human
contract (frozen 2026-09-18); this file is the registry-bound
preregistration for the GBPUSD sleeve — the first hypothesis ID declared
in that contract.

## Delta vs killed neighbors (declared up front)

- `HYP-LSWEEP-EUR/XAU-M5-001` (killed 2026-09-12/18): the complementary
  direction. LSW bet on penetration *reversion* at reference levels and
  died on cadence (0.05–0.12/wk) and economics. SD bets on session-open
  penetration *persistence* — a denser object (~15 events/wk pre-filter by
  the Stage-0 probe). Not a rescue: different trigger, direction, stop
  anchor, and signal density.
- `EA_NYOpeningDriveContinuation` (archive, never ran): same family name,
  different object — it was a single-session NY drive with a prior-2h-range
  gate and body/close-location filters on M15; SD is the canonical
  3-session M5 ORB with OR-midpoint stop. New hypothesis, not a revival.
- `HYP-ECRS-EURUSD-M5-001/002` (parked stage-0): compression-breakout —
  died on cadence because the compression gate made events rare. SD has no
  compression precondition: the session OR alone defines the level, which
  is why its frequency check passed (~15/wk).
- Era-2 breakout cells (`M15BR-EU`, `FVG-EU`, `H1D-EUR`, killed): range/
  displacement breakouts on EURUSD — different level source (rolling
  lookback/displacement, not session-anchored opening range) and different
  symbol. SD's stop anchor (OR mid, ~0.5×OR) is structurally wider relative
  to cost than their tight stops.

## Hypothesis (frozen)

- **Mechanism:** Session opening-drive continuation (ORB). Each of the
  three GMT liquidity sessions (Asia 00–07, London 07–16, NY 12–20) opens
  with a directional drive; the first `or_bars=4` closed M5 bars define the
  opening range, and the first later M5 close beyond an OR extreme is
  traded as continuation.
- **OR validity:** `or_range ∈ [0.5, 6.0] × ATR14`; OR bars exactly
  contiguous (a gap kills the session occurrence).
- **Break window:** `[OR end, OR end + 48 bars]` inside the session;
  margin zero — the canonical close-beyond-extreme trigger.
- **Direction:** close > ORH → long; close < ORL → short. Max 1 entry per
  session.
- **Exits:** SL = OR midpoint ± 0.10 × ATR, floored at 4× spread
  (broker-side, via shared `LswBuildPlan`); TP = 1.30R; time stop 24 M5
  bars; break-even at 0.70R; daily flat server ≥ 22; Friday flat ≥ 20.
- **Symbol / timeframe:** GBPUSD, M5 closed-bar decisions.
- **Sessions:** Asia + London + New York on the derived GMT clock (server
  offset +2 winter / +3 US DST); rollover hours 23/0 server excluded.
- **Sizing:** 0.35% equity risk per trade; margin-capped; max 6
  entries/day; daily loss lock 2%; account DD lock 10%; streak lock 4.
- **News:** ±20 min high-impact blackout; fail-open counted via
  `news_query_empty`.
- **Decision semantics:** closed-bar only; stdlib iATR; no custom
  indicator. Execution via shared AF_ExecutionKernel.

## Environment (frozen)

- **Broker/server:** MetaQuotes Ltd. / MetaQuotes-Demo (AlphaFactory
  portable isolate `mt5-portable-mqdemo`). RESEARCH-ONLY, non-promotable.
- **Coverage mode:** `all_available_asof` — From=1999.01.01,
  To=2026.09.11, reproducing the proven era-2 GBPUSD M5 data fingerprint
  (99% / 2,045,400 bars / 429,467,282 ticks).
- **Model:** 0 (every tick generated from M1 bars; not broker real ticks).
- **Cost tier:** `research_proxy`. Spread = tester `current` (measured
  GBPUSD window). Commission = conservative bound $7.00/lot RT.
  Slippage = independent-quote measured proxy.
- **Clock open item:** the first journal `SD001_CLOCK_DIAG` line must show
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
Dropping a session post-hoc is a new hypothesis, not a revision.

## Kill criteria (frozen)

- Gross result ≤ 0 after modeled costs, or cadence < 10 trades/week.
- Engineering invalidity that cannot be repaired without changing the
  frozen signal semantics (that repair becomes a new hypothesis row).

## Non-goals

- No promotion, no demo deployment, no live inference from this packet.
- No pooled P&L with the queued USDJPY sleeve; GBPUSD stands alone.
