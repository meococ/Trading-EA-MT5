# HYP-RGR-CHF-M1-001 — FROZEN PREREG (Roll-Gap Reversion, USDCHF sleeve)

Frozen before build and before any governed observation of this mechanism.
Frozen at: 2026-09-19. Amendment only via a new hypothesis ID.

## Mechanism (measured, not invented)

At server 00:00 the FX day reopens after the 5pm-ET roll pause. The reopen
systematically prints below fair value (tom-next/carry repricing overshoots in
the post-roll liquidity vacuum). Buy the reopen; exit when the ~2h reversion
completes. Verified on the tester M1 .hcc plane 2010→2025 (~370k bars/yr,
event-level): gap ≤ −1.5p → +2.2–2.6p @60m, PF 2.0–4.3, t 6–15, win 65–80%,
7/7 majors + XAUUSD at its own boundary; stable post-2016, both DST regimes.
USDCHF additionally reverts gap-UPS (PF 2.5–6.7). See
`04. Memory/research/20260919_ROLL_GAP_REVERSION_DEEP_HISTORY.md`.

This is NOT the withdrawn pierce-fade: the trigger is the reopen GAP SIZE, not
a range pierce, and entry is ~5min into the reversion (overshoot peak), not a
fade of the spike.

## Spec (all parameters frozen)

- Symbol: **USDCHF** (strongest PF 4.28–5.22 + the only live short side).
- Timeframe: **M1** (entry precision at ~00:05).
- Day-boundary detection: first M1 bar whose server date differs from the
  previous bar's server date. `gap_pips = (day_open − prev_close)/pip`.
  Feed-agnostic (works whether the roll pause is 1 or 30 minutes).
- **LONG**: gap ≤ −1.5p. **SHORT**: gap ≥ +2.0p (USDCHF gap-up side only).
- Entry: market order on the first bar with server day-minute in [4, 8]
  (≈00:05; measured optimum — overshoot peaks ~5min after reopen).
  One entry per direction per day.
- Exit: **SL = 15.0p fixed** (MAE med −3~−5p, p25 −8.9p; SL sweep 6→20p:
  12–15p is the plateau). **TP = 10R** non-binding. **Time-stop = position
  age ≥ 120 min** (PF peaks at 120m hold; reversion completes ~2h).
- Hard flats inherited: daily flatten ≥22h server, Friday ≥20h server,
  weekend. Positions open 00:0x, close by ~02:0x — no overnight, no weekend.
- Filters: risk 0.35%/trade; max 2 entries/day (one per direction); spread
  cap OFF (measured p90 0.2–0.3p at the window); news blackout enabled
  (safety, rarely binds at 00:05); no rollover veto — the rollover window IS
  the mechanism; all times SERVER — no GMT conversion in the signal path.
- Clock: server-time gating only (auditor fix — prior BEDGE/SMOM runs were
  clock-corrupted by GMT gates shifted +2–3h from probed windows).

## Declared expectations (pre-registered)

- Cadence: ~60 long + ~6 short events/yr ≈ **~1.3 trades/week — BELOW the
  GOAL floor of 10/wk, declared up front**. This run validates governed
  economics of the first verified mechanism; cadence feasibility is a
  separate contract question (supplementary legs still unfalsified: none
  confirmed after WMR/ECB/Tokyo-fix and 23h legs died).
- Economics: probe PF 2.0–4.3 gross; vs ~1.5–2p all-in cost (spread+comm+
  adverse-fill) net PF plausibly ~1.3–2. Governed run decides.

## Kill criteria (frozen)

- **Dead**: governed PF < 1.30 after cost ×1, OR executed cadence < 1.0/wk,
  OR per-year sign flips negative on the run window.
- **Marginal**: PF 1.30–1.60 → one narrow revision allowed (gap threshold OR
  exit horizon, not both).
- **Alive**: PF > 1.30 and mechanism signature intact → evaluate second
  sleeve (USDCAD/XAUUSD) and the cadence question vs GOAL.

## Anti-overfit declarations

- One cell (USDCHF, day-boundary gap) minted from a verified family; no
  parameter search — all values from the measurement plateau, not the max.
- n≈60–100 events/yr is thin for year-splitting; quarterly/win-rate drift
  (2025→26) is reported, not hidden.
- The mechanism is a single conditional event per day; no tranche/ladder
  counting toward cadence.
