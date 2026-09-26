# SF01 / F5 — SECOND ENTRY (H2/L2 two-legged pullback) — a priori spec v2

(v2: `inv` moved to the deepest point of the two-legged pullback —
min(l[i1],l[i2]) for longs — per DECISIONS D10; v1's pivot-bar stop
failed the 10x cost floor on ~84% of candidates. Pre-outcome revision.)

Frozen before any outcome computation. Any rule change requires a new spec
version + new ledger hash. ENGINE semantics are the frozen referee
(`pa_fill`); per-entry SL/TP prices are NOT expressible there, so structural
geometry is enforced as signal gates + the S ladder (D1, Lead-accepted).

## Rationale

Brooks' second entry: in a trend, the first pullback low (L1 in an
uptrend) is often faded too early; the second leg down produces L2, and
the resumption off L2 is the higher-probability entry — two-sided
participants have been flushed twice. Mirror for downtrends (H1/H2
highs). We enter with a stop order above the L2 bar (Volman-style: stop
beyond the signal bar, not after the break).

Distinct from F4: F4 requires a ZONE pullback; F5 is pure price
structure (two confirmed swing legs), no zone involvement — the family's
independence is the point.

## Causal inputs (all known at close of M5 bar t)

From `families/sf_ctx` cache:

- `piv_idx/piv_px/piv_side/piv_conf`: confirmed M5 pivots
  (pivot bar, price, side -1 low / +1 high, confirmation bar).
  A pivot at bar `i` is knowable only at `piv_conf[i]`.
- `s_tr_h1[t]` / `s_tr_h4[t]`: trend sign, causal.
- `o/h/l/c[t]`; `atr_m5[t]`; `t` for the session gate; `warmup`.

## Signal rules (bar t)

Fire exactly at the confirmation bar of the second leg's pivot:

1. `tr = s_tr_<src>[t]` in {+1,-1}; `tr==0` -> skip.
2. LONG (`tr=+1`): let the confirmed-low list be L; take the latest two
   lows `L1=(i1,px1,cf1)`, `L2=(i2,px2,cf2)` with `cf2 == t`
   (this bar just confirmed L2).  Require:
   - a confirmed swing HIGH `H=(ih,pxh,cfh)` with `i1 < ih < i2`
     and `cfh <= t` — the bounce between the two legs;
   - `i2 - i1 <= leg_span` (=48 bars) — a pullback, not a new regime;
   - `|px2 - px1| <= tol_atr * atr_m5[t]` — L2 retests the L1 area
     (lower, equal, or marginally higher all qualify);
   - resumption already underway: `c[t] > h[i2]` would be chasing — we
     only require `c[t] >= l[i2]` (price off the low) plus the order
     itself being a stop ABOVE the L2 bar (see geometry), which does the
     work;
   - session gate (D3); `h[t]-l[t] >= 0.5*atr_m5[t]` range gate;
     cooldown 12 bars; one signal per `i2` (dedupe by pivot identity).
3. SHORT: mirror with swing highs H1, H2 and a confirmed LOW between
   them; `cf(H2) == t`.

## Order geometry

- Entry: STOP beyond the second-leg pivot bar —
  long: `order_px = h[i2] + 1pip`; short: `order_px = l[i2] - 1pip`.
- `inv`: the deepest point of the two-legged pullback (Brooks: stop
  below the pullback low) —
  long: `inv = min(l[i1], l[i2]) - 1pip`;
  short: `inv = max(h[i1], h[i2]) + 1pip`.
- `s_struct = |inv - order_px|`; smallest
  ladder rung `>= s_struct`, `>= 10 * c_rt`, `<= 32` pips.
- Target: `tp_mult * S`, `tp_mult = 2.0` (fixed-R).

## Expiry / management

- `v_bars = 3`; `session_cancel = True`; flats as standard; no BE/trail.

## Dedupe

- One signal per confirmed pivot `i2`; per-symbol cooldown 12 bars;
  one signal per bar.

## Config grid (20 <= 24 budget)

    S_pips       in {11, 14, 18, 24, 32}
    tr_src       in {h1, h4}
    tol_atr      in {0.5, 1.0}
    fixed: tp_mult=2.0, buf=1.0, v_bars=3, min_range_atr=0.5,
           leg_span=48, pivot strength k=3, cooldown=12, session eu|us.
