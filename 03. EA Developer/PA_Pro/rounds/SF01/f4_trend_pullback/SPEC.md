# SF01 / F4 — TREND PULLBACK TO ZONE — a priori spec v1

Frozen before any outcome computation. Any rule change requires a new spec
version + new ledger hash. ENGINE semantics are the frozen referee
(`pa_fill`); per-entry SL/TP prices are NOT expressible there, so structural
geometry is enforced as signal gates + the S ladder (D1, Lead-accepted).

## Rationale

The highest-quality zone trade is the one aligned with the higher-timeframe
trend: in an H1/H4 uptrend, a pullback down into a floor zone is profit
taking, not reversal — when momentum resumes (bar closes back above the
band top AND above the previous bar's high), the trend leg restarts. We
buy the resumption. Mirror for downtrends.

Distinct from F1 (zone rejection, no trend context — dead on screen) and
F2 (post-break retest). F4 requires BOTH: a live trend reading AND a zone
pullback with momentum resumption.

## Causal inputs (all known at close of M5 bar t)

From `families/sf_ctx` cache for `(symbol, gen)`:

- `s_tr_h1[t]` / `s_tr_h4[t]`: structural trend sign (-1/0/+1) from the
  last two confirmed pivots + EMA20/50 alignment of the H1 (resp. H4)
  stack, causal at the close of bar t.
- `zones_at(t)`: armed zones strongest-first with `broken`,
  `approach_side`, `touches`, `last_touch`, band `[lo, hi]`, `zid`.
- `o/h/l/c[t]`; `atr_m5[t]`; `t` for the session gate;
  `first_live_idx` / `warmup`.

## Signal rules (bar t)

1. Trend: `tr = s_tr_<src>[t]` in {+1, -1}; `tr == 0` -> skip.
2. Pick the FIRST zone in `zones_at(t)` (strongest-first) satisfying:
   - `armed == 1`, `broken == 0`;
   - `approach_side == tr` (uptrend: floor below price, `ap == +1`;
     downtrend: ceiling above price, `ap == -1`);
   - `touches >= touches_min` (=1);
   - pullback present: `last_touch` within `[t - pull_win, t]`
     (`pull_win = 24` bars) — price recently entered the band;
   - not in per-`zid` cooldown (12 bars); the (zid, last_touch) episode
     has not already produced a signal.
3. Momentum resumption at bar t:
   - LONG:  `c[t] > z.hi` AND `c[t] > h[t-1]`;
   - SHORT: `c[t] < z.lo` AND `c[t] < l[t-1]`;
   - if `rej_body == 1`: `c[t] > o[t]` (long) / `c[t] < o[t]` (short);
   - bar range gate: `h[t] - l[t] >= 0.5 * atr_m5[t]`.
4. Session gate (D3): signal bar closes in eu|us.
5. `side = tr`.

## Order geometry

- Entry: STOP order beyond the signal bar —
  long: `order_px = h[t] + 1pip`; short: `order_px = l[t] - 1pip`.
- `inv`: pullback extreme since the touch —
  long: `min(l[last_touch..t]) - 1pip`;
  short: `max(h[last_touch..t]) + 1pip`.
- `s_struct = |inv - order_px|`; smallest ladder rung `>= s_struct`,
  `s_struct >= 10 * c_rt_pips`, `<= 32` pips; configs partition.
- Target: `tp_mult * S`, `tp_mult = 2.0` (fixed-R, charter-legal).

## Expiry / management

- `v_bars = 3`; `session_cancel = True`; `daily_flat_hour = 22`,
  `friday_flat_hour = 20`, `weekend_veto = True`, `legacy_flats = False`.
  No break-even / trailing / partials.

## Dedupe

- One signal per `(zid, last_touch)` episode; per-`zid` cooldown 12 bars;
  one signal per bar.

## Config grid (20 <= 24 budget)

    S_pips       in {11, 14, 18, 24, 32}   (ladder rung)
    gen          in {line1_cluster, sd_base}
    tr_src       in {h1, h4}
    fixed: tp_mult=2.0, buf=1.0, v_bars=3, min_range_atr=0.5,
           touches_min=1, pull_win=24, cooldown=12, session eu|us.
