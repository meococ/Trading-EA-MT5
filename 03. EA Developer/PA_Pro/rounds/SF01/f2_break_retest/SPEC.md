# SF01 / F2 — BREAK-AND-RETEST — a priori spec v2

Frozen before any outcome computation. Any rule change requires a new spec
version + new ledger hash. ENGINE semantics are the frozen referee
(`pa_fill`); per-entry SL/TP prices are NOT expressible there, so structural
geometry is enforced as signal gates + the S ladder (D1, Lead-accepted).

## Rationale

A decisive close through a zone (`broken_idx` set: close beyond the far
band edge by > `break_atr` x ATR14(H1)) marks a level failure. The classic
continuation play: price pulls back INTO the broken band, the retest is
rejected (close back out on the break side), and the move resumes — the
broken ceiling becomes a floor. The episode spans the engine's
break -> (reclaim | flip) lifecycle: a retest may occur while the zone is
still broken (`break_keep_bars` = 192) or after `role_flip` confirms it;
the anchor is the break bar either way. We trade the FIRST post-break
pullback rejection, in the break direction.

The matched-random baseline enters at the same session/dow/month cells
with identical S/tp geometry, so positive lift means the break+retest
event itself carries information.

## Causal inputs (all known at close of M5 bar t)

From `families/sf_ctx` cache for `(symbol, gen)`:

- `zones_at(t)`: live near-price zones strongest-first with `armed`,
  `broken`, `broken_idx`, `role_flip`, `broken_side`, `approach_side`,
  `touches`, `last_touch`, band `[lo, hi]`, `zid`.
- `o/h/l/c[t]`; `atr_m5[t]`; `t` (server epoch) for the session gate;
  `first_live_idx` / `warmup` (no signals on warm-up bars).

Detector-tracked per-`zid` state (causal, past-only):

- `anchor[zid]`: episode anchor = `broken_idx` while broken; when the
  zone is first observed with `role_flip == 1`, the anchor stays if a
  broken-phase anchor exists, else the flip-observation bar.
- `ft_touch[zid]`: first `last_touch` strictly after `anchor` (first
  post-break pullback episode), latched once.
- `fired[zid]`: at most one signal per anchor episode.

## Signal rules (bar t)

1. Pick the FIRST zone in `zones_at(t)` (strongest-first) satisfying:
   - episode active: `broken == 1` OR `role_flip == 1`;
   - `broken_side != 0`; `touches >= touches_min` (=1);
   - role consistency: `approach_side == side` where
     `side = -broken_side` (price must approach from the post-break side:
     broken ceiling (`broken_side = -1`, broke up) -> LONG retest from
     above; broken floor (`broken_side = +1`, broke down) -> SHORT retest
     from below);
   - post-anchor retest present: `ft_touch` exists AND
     `t - ft_touch <= retest_win` (=48 bars);
   - not `fired`, not in per-`zid` cooldown (12 bars).
2. Rejection bar t (close crosses back OUT of the band on the break
   side — continuation):
   - LONG:  `c[t] > z.hi` AND `c[t-1] <= z.hi`;
   - SHORT: `c[t] < z.lo` AND `c[t-1] >= z.lo`;
   - if `rej_body == 1`: `c[t] > o[t]` (long) / `c[t] < o[t]` (short);
   - bar range gate: `h[t] - l[t] >= 0.5 * atr_m5[t]`.
3. Session gate (D3, a priori): the signal bar must close inside the eu
   (05:00-11:00 UTC) or us (11:30-17:30 UTC) window — the same universe
   the matched-random baseline draws from.
4. `side = -broken_side`.

## Order geometry

- Entry: STOP order beyond the signal bar —
  long: `order_px = h[t] + 1pip`; short: `order_px = l[t] - 1pip`.
- `inv` (pre-fill invalidation): the pullback extreme since the retest
  touch — long: `min(l[ft_touch..t]) - 1pip`;
  short: `max(h[ft_touch..t]) + 1pip`.
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

## Dedupe

- At most one signal per `zid` per anchor episode (`fired`).
- Per-`zid` cooldown 12 bars; at most one signal per bar.

## Config grid (20 <= 24 budget)

    S_pips       in {11, 14, 18, 24, 32}   (ladder rung)
    gen          in {line1_cluster, sd_base}
    rej_body     in {0, 1}
    fixed: tp_mult=2.0, buf=1.0, v_bars=3, min_range_atr=0.5,
           touches_min=1, retest_win=48, cooldown=12, session gate eu|us.

## HISTORY

- v1 (sha a3f8baac, ledger T000071): role_flip==1 required (confirmed
  flip only), anchor = flip-observation bar. Never screened: DESIGN
  census (pre-outcome) showed ~5.3 signals/week basket and most grid
  cells below the N>=300 gate. Superseded before any outcome (D8).
- v2: anchor = break bar; episode spans break -> reclaim | flip; same
  retest+rejection semantics. Census-first revision, no outcomes seen.
