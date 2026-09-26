# SF01 / F3 — FAILED BREAKOUT / TRAP — a priori spec v1

Frozen before any outcome computation. Any rule change requires a new spec
version + new ledger hash. ENGINE semantics are the frozen referee
(`pa_fill`); per-entry SL/TP prices are NOT expressible there, so structural
geometry is enforced as signal gates + the S ladder (D1, Lead-accepted).

## Rationale

A break that fails is a trap: breakout traders are caught on the wrong
side and their exits fuel the reversal. In engine terms the event is a
RECLAIM — a zone whose `broken` state is cleared because price closed
back inside the band (+`break_atr` pad) within `reclaim_bars` (96) of the
break, i.e. before the flip deadline. The reclaim close is the trap
confirmation; we fade the failed break, trading back toward/through the
zone interior.

This is the mirror image of F2 (which trades the retest that holds).
F3's population is disjoint by construction: F2 fires on post-anchor
touch + rejection in the break direction; F3 fires on the reclaim close
itself. A zone episode can produce at most one of the two.

The matched-random baseline enters at the same session/dow/month cells
with identical S/tp geometry, so positive lift means the trap event
itself carries information.

## Causal inputs (all known at close of M5 bar t)

From `families/sf_ctx` cache for `(symbol, gen)`:

- `zones_at(t)`: live near-price zones strongest-first with `broken`,
  `broken_idx`, `role_flip`, `broken_side`, `approach_side`, `touches`,
  band `[lo, hi]`, `zid`.
- `o/h/l/c[t]`; `atr_m5[t]`; `t` for the session gate;
  `first_live_idx` / `warmup` (no signals on warm-up bars).

Detector-tracked per-`zid` state (causal, past-only):

- `prev_broken[zid]`: the `broken_idx` value observed on the most recent
  bar where the zone appeared with `broken == 1`.
- `brk_hi[zid]` / `brk_lo[zid]`: running max/min of `h`/`l` over bars in
  `[anchor, t]` while the episode is live (probe extreme).

## Signal rules (bar t)

1. RECLAIM event on zone z: the zone was observed `broken == 1` at bar
   `t-1` (`prev_broken[zid]` set) and at bar t shows `broken == 0` AND
   `role_flip == 0` — i.e. the engine cleared the break by a close back
   inside `(lo - break_pad, hi + break_pad)` before the flip deadline.
   (A flip — `role_flip` turning 1 — is NOT a reclaim; it is F2's
   continuation regime and must not fire here.)
2. Direction = opposite of the failed break:
   `side = +broken_side` — a broken ceiling (`broken_side = -1`, failed
   up-break) -> SHORT; a broken floor (`broken_side = +1`, failed
   down-break) -> LONG.
3. Filters at bar t:
   - `touches >= touches_min` (=1);
   - break recency implied by the engine (reclaim only exists
     `<= reclaim_bars` after the break);
   - session gate (D3): signal bar closes in eu|us;
   - bar range gate: `h[t] - l[t] >= 0.5 * atr_m5[t]`;
   - optional `rej_body == 1`: reclaim bar body in the fade direction
     (`c[t] < o[t]` for short / `c[t] > o[t]` for long);
   - at most one signal per (zid, break episode) — `fired` latch;
     per-`zid` cooldown 12 bars; one signal per bar (strongest zone).

## Order geometry

- Entry: STOP order in the fade direction beyond the reclaim bar —
  short: `order_px = l[t] - 1pip`; long: `order_px = h[t] + 1pip`.
- `inv` (pre-fill invalidation): the probe extreme of the whole trap —
  short: `max(h[anchor..t]) + 1pip`; long: `min(l[anchor..t]) - 1pip`
  (`anchor` = the break bar `prev_broken[zid]`).
- Structural stop distance `s_struct = |inv - order_px|`.
- **S ladder** (D1): `LADDER = {11, 14, 18, 24, 32}` pips; emitted into
  config `S` iff `S` is the smallest rung `>= s_struct` AND
  `s_struct >= 10 * c_rt_pips`. `s_struct > 32` pips skipped. Configs
  partition the signal set.
- Target: engine `tp_mult * S`, `tp_mult = 2.0` (fixed-R, charter-legal).

## Expiry / management

- Pending validity `v_bars = 3` M5 bars; `session_cancel = True`;
  `daily_flat_hour = 22`, `friday_flat_hour = 20`, `weekend_veto = True`,
  `legacy_flats = False`. No break-even / trailing / partials.

## Config grid (20 <= 24 budget)

    S_pips       in {11, 14, 18, 24, 32}   (ladder rung)
    gen          in {line1_cluster, sd_base}
    rej_body     in {0, 1}
    fixed: tp_mult=2.0, buf=1.0, v_bars=3, min_range_atr=0.5,
           touches_min=1, cooldown=12, session gate eu|us.
