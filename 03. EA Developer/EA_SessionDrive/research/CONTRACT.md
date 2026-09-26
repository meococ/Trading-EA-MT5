# CONTRACT — Session Drive (SD)

Version 1.0 — 2026-09-18

This document is the frozen authority for the `EA_SessionDrive` package.
Behaviour in code that contradicts this contract is a defect to fix; behaviour
desired that contradicts this contract requires a NEW hypothesis.

## 1. Hypothesis

**Opening-drive continuation (ORB).** Each of the three GMT liquidity
sessions (Asia 00:00–07:00, London 07:00–16:00, New York 12:00–20:00) opens
with a directional drive. The first `or_bars` closed M5 bars define the
opening range; the first later M5 close beyond an OR extreme is traded as
continuation of that session's drive.

This is the direct complement of the killed LSW sweep-fade family: LSW bet
that level penetration reverts (it lost, PF 0.48–0.68 at cost). SD bets that
session-open penetration *persists*. The falsification is symmetric and
independent — an OR break is not an LSW level sweep (no close-back
requirement, no bounded-penetration band, opposite direction).

### Prior evidence (declared before outcomes)

- Stage-0 frequency probe (`tools/probe_session_drive_cadence.py`, 92 days,
  governed isolate): ~15 candidate entries/week per symbol (USDJPY 14.8,
  GBPUSD 14.9, XAUUSD 15.0) at the frozen geometry — inside the 10–40/week
  band. Frequency-plane check only; no outcome was read.
- Historical session-windowed edges exist in the archive (SilverBullet
  USDJPY KZ+FVG PF 1.28–1.32 @ ~2/wk — real but sub-cadence; SMC NY-session
  PF 1.36–1.61 @ ~1/wk — sub-cadence). SD's 3-session ORB is a different,
  denser object.
- Era-2 kill board shows single-object intraday scalps die on economics at
  MQ-Demo cost (median cost drag ~30% of PF). SD counters with a wider
  structural stop (risk ≈ 0.5×OR ≈ 1.25×ATR median) — cost ≈ 10–20% of R
  vs LSW's 40–60% — and a per-session FSM rather than a single trigger.

## 2. Instrument, clock and data

- Symbol: per-sleeve (GBPUSD first; USDJPY second). M5 closed bars only.
- Server→GMT derivation is the LSW doctrine, verbatim:
  `gmt = server − (offset + dst)·3600`, `offset=2`, US-DST rule +1h
  (`LswServerToGmt`, `LswUsDstActive`). `TimeGMT()` is never used for a
  decision; the measured delta is printed once as `SD001_CLOCK_DIAG`.
- Session membership is computed on the CLOSED bar's own GMT stamp.
- Flatten/rollover/weekend checks use raw SERVER time (same doctrine as LSW:
  `unified_validation.py` classifies overnight exposure on server dates).
- Data split: full available history, Model 0 only.

## 3. Decision semantics — closed bar, no exceptions

- All geometry reads `shift >= 1` M5 bars. The forming bar contributes its
  timestamp only.
- One decision per closed bar; `g_last_bar_time` guards duplicates.
- Restart-safety: position mirror rebuilt from the terminal every tick;
  session FSM state is bar-derived and repopulates from history.

## 4. Session FSM (`Include/SD_Signal.mqh`)

Three independent per-session state machines (ASIA/LDN/NY), reset per GMT
day:

1. **Forming** — bars with `gmt_min ∈ [open, open+20)` accumulate OR high/low.
   Requires exactly `or_bars` contiguous M5 bars; any gap inside the window
   kills the session (`geom_or_gap`).
2. **OR validation** — at `or_count == or_bars`: valid iff
   `or_range ∈ [or_min_atr, or_max_atr] × ATR14`. Below floor → `geom_or_small`
   (no drive); above cap → `geom_or_large` (drive already spent).
3. **Armed** — bars with `gmt_min ∈ [open+or_span, open+or_span+break_span)`:
   first closed bar with `close > ORH` fires LONG, `close < ORL` fires SHORT.
   Margin is zero (canonical ORB trigger). Session consumed on first fire.
4. **Expired** — armed but no break before window end → `geom_no_break`.

LDN (07–16) and NY (12–20) windows overlap, but each session's *armed* window
ends before the next session's OR completes (LDN armed ends 11:20 GMT, NY OR
starts 12:00 GMT), so at most one session can break on any given bar.
Sessions are checked in open order (ASIA → LDN → NY).

## 5. Entry

- Signal: `SdDetectDrive` returns a `SdDrive` (direction, session, ORH/ORL,
  OR midpoint, ATR, break-bar close).
- Entry: market order at the break bar's close (next-bar open in tester),
  direction = break direction.
- Max 1 entry per session; max `max_trades_per_day` entries per server day;
  1 position per symbol at any time.

## 6. Exit

- SL anchor: **OR midpoint** (a break retracing through mid-OR means the
  drive failed), padded `sl_buffer_atr × ATR` beyond it, floored at
  `min_sl_spread_mult × spread`. Computed by the shared `LswBuildPlan` via
  the `SdDriveToSweep` adapter (`extreme = or_mid`).
- TP: `tp_r` × risk distance (frozen 1.30R), rounded to tick.
- Time stop: `max_hold_bars` M5 bars (frozen 24 = 2h).
- Break-even: at `be_at_r` (frozen 0.70R), SL → entry, once.
- Hard flats: server `flatten_hour` (22:00) and Friday `friday_flatten_hour`
  (20:00) — overnight/weekend holding is structurally impossible.
- Exits evaluated every tick; close attempts throttled to 5/bar.

## 7. Position sizing

Shared `LswBuildPlan` path, unchanged:

- `money_per_lot` = max(tick-value estimate, |OrderCalcProfit|), both in
  deposit currency; if both routes fail → reject.
- `volume = equity × risk_percent/100 / money_per_lot`, normalized DOWN to
  broker step; margin ≤ 50% free margin.
- Frozen `risk_percent = 0.35`.

## 8. Filters, exposure and safety locks

Each filter increments exactly one counter and returns:

- Session clock: entries blocked on weekend / rollover (server 23h–00h) /
  flatten windows. (Session membership itself is FSM-guaranteed.)
- Ownership: any open position or pending order on the symbol blocks.
- Kernel: must be `AF_EXEC_IDLE`.
- Risk locks: daily loss `2%`, account DD `10%`, consecutive losses `4`,
  max trades/day `6`.
- ATR floor: `atr ≥ min_atr_points × point` (frozen 40 pts GBPUSD).
- Spread: `spread ≤ max_spread_atr × ATR` (frozen 0.20).
- News: high-impact release in either leg currency within ±20 min blocks
  the entry; calendar query failure is fail-open with a counter
  (`news_query_empty`).

## 9. Cost, slippage and swap assumptions

- Tester spread: pinned to measured evidence (per-symbol sidecar), not the
  default.
- Slippage/commission modeled post-run by `build_verified_cost_artifact.py`
  at x1 / x1.5 / x2 stress tiers.
- Swap: sessions close intraday (max hold 2h, hard flats) → swap ≈ 0.
- Research-proxy costs are non-promotable (GOAL §8).

## 10. Data split

- Baseline: full available history (as-of run), Model 0, one shot.
- No holdout/OOS read before configuration freeze. No post-hoc subgroup,
  year, hour, or direction salvage.

## 11. Researchable parameters and trial budget

Frozen baseline values (M5, all sleeves unless noted):

| Parameter | Value |
|---|---|
| `or_bars` | 4 (20 min) |
| `or_min_atr` / `or_max_atr` | 0.5 / 6.0 × ATR14 |
| `break_bars` | 48 (4h) |
| `sl_buffer_atr` | 0.10 × ATR (beyond OR midpoint) |
| `min_sl_spread_mult` | 4.0 |
| `tp_r` | 1.30R |
| `max_hold_bars` | 24 |
| `be_at_r` | 0.70R |
| `max_spread_atr` | 0.20 |
| `min_atr_points` | 40 (GBPUSD) / set per sleeve |
| `news_blackout_min` | ±20 |
| `risk_percent` | 0.35 |
| `max_trades_per_day` | 6 |
| `max_consecutive_losses` | 4 |
| `max_daily_loss_pct` / `max_account_dd_pct` | 2.0 / 10.0 |
| `flatten_hour` / `friday_flatten_hour` (server) | 22 / 20 |

**Budget: baseline + at most 2 market-logic revisions per hypothesis.**
A revision may change one coherent parameter axis (e.g., OR geometry, exit
geometry). Adding/removing a filter is a revision. A different mechanism is
a new hypothesis, not a revision.

## 12. Known uncertainties, declared up front

1. **Overlap asymmetry**: NY OR forms 12:00–12:20 GMT inside the London
   session — a live LDN position blocks the NY entry (`filt_position_open`).
   Expected attrition is small (LDN trades resolve in ≤2h) but nonzero.
2. **Asia quality**: the Asia drive is the weakest documented session;
   its inclusion is for cadence buffer, and per-session attribution in
   `SD001_SUMMARY_SESSION` makes its contribution auditable. A revision may
   NOT drop a session post-hoc — that is a different hypothesis.
3. **Zero-margin trigger**: any 1-tick close beyond the OR fires. If weak
   marginal breaks dominate, the honest fix is a revision (confirmation
   margin), not silent filtering.
4. **Server clock drift**: DST-rule edges can shift sessions ±1h on switch
   days; declared and accepted (same as LSW §12.3).
5. **News calendar coverage** on the tester is partial; fail-open with
   counter keeps this visible.

## 13. PASS / KILL

### PASS (all must hold, on the same frozen config)

- Report PF and cost-tier PF x1 > 1.30; x1.5 ≥ 1.25; x2 ≥ 1.00.
- Cadence 10–40 trades/week (validator's elapsed-calendar formula).
- Max DD ≤ 15% (MC P95 within preregistered budget).
- History quality > 97%; overnight = 0; weekend = 0; equity audit clean.
- Non-repaint audit PASS on the exact source/include snapshot.

### KILL

- Net ≤ 0 after modeled cost at x1, OR
- Cadence < 10 trades/week, OR
- Engineering invalidity unrepairable without changing frozen signal
  semantics, OR
- Budget exhausted without PASS.

### Not a KILL

- Engineering defects fixable inside frozen semantics (a bug in the FSM,
  sizing, telemetry) — fix and rerun counts as the same trial.

## 14. Freeze record

| Field | Value |
|---|---|
| Family | `EA_SessionDrive` |
| Hypotheses | `HYP-SDRIVE-GBP-M5-001` (GBPUSD), `HYP-SDRIVE-UJ-M5-001` (USDJPY, queued) |
| Signal | session OR break → continuation market entry |
| Substrate | LSW_* modules (clock/news/risk/plan), AF kernel, lifecycle-v3 |
| Created | 2026-09-18 |
