# SF01 / F6 — VOLMAN BOX BREAK with buildup — a priori spec v2

(v2: `box_atr` re-scaled {0.7,0.9} -> {2.5,4.0} per DECISIONS D11 — v1's
threshold was calibrated to per-bar width, not the 12-bar window height,
and produced zero candidates. Pre-outcome correction.)

Frozen before any outcome computation. Any rule change requires a new
spec version + new ledger hash. ENGINE semantics are the frozen referee
(`pa_fill`); per-entry SL/TP prices are NOT expressible there, so
structural geometry is enforced as signal gates + the S ladder
(D1, Lead-accepted).

## Rationale

The DR3 lineage: Volman's box break. Price compresses into a tight
M5 box that presses against a structural level (armed zone edge); the
break is entered with a STOP order 1 pip beyond the box edge — the
entry happens AT the break, not after it (the DR3 lesson: entering
after the break bar is chasing). DR3 showed picture fidelity is not
edge; this family's economic screen against matched-random identical
geometry is the honest test. What is new vs DR3: causal zone-level
buildup context (the box must press against a live armed zone), the
correct stop-order entry, and the structural S ladder.

Distinct from F2/F3: F2 trades the retest AFTER a break; F3 trades a
FAILED break (reclaim); F6 trades the break itself from a compressed
base.

## Causal inputs (all known at close of M5 bar t)

From `families/sf_ctx` cache:

- `zones_at(D, t)`: live zones with `armed`, `lo`, `hi`, `zid`,
  `approach_side`, `touches`, `last_touch`.
- `o/h/l/c[t]`; `atr_m5[t]`; `t` for the session gate; `warmup`.

## Signal rules (bar t)

1. BOX (compression): over the last `B=12` bars `[t-B..t-1]` (signal
   bar excluded), `box_hi = max h`, `box_lo = min l`, and
   `box_hi - box_lo <= box_atr * atr_m5[t]`.
2. BUILDUP (structural context — required): an armed zone at t with
   - LONG: `approach_side == -1` (ceiling) and
     `|zone.hi - box_hi| <= prox_atr * atr_m5[t]` — the box top is
     pressed against the ceiling edge;
   - SHORT: `approach_side == +1` (floor) and
     `|zone.lo - box_lo| <= prox_atr * atr_m5[t]`.
3. TRIGGER: signal bar closes through the box edge AND the zone edge:
   - long: `c[t] > box_hi + buf` AND `c[t] > zone.hi`;
   - short: `c[t] < box_lo - buf` AND `c[t] < zone.lo`.
   - signal bar range >= `min_range_atr * atr_m5[t]`.
4. Session gate (D3); per-symbol cooldown 12 bars; one signal per
   (zone, box) episode — dedupe by `zid` + the box end bar: after a
   signal fires for `zid`, suppress further signals on that `zid` for
   `cooldown` bars.

## Order geometry (the Volman entry)

- Entry: STOP order 1 pip beyond the box edge —
  long: `order_px = box_hi + 1pip`; short: `order_px = box_lo - 1pip`.
  Because `c[t]` is already beyond `order_px` at the signal close, the
  referee fills on the NEXT bar's path (an immediate fill at/better
  than the stop level) — the honest equivalent of Volman's resting
  stop placed as the box forms.
- `inv`: the far side of the box —
  long: `inv = box_lo - 1pip`; short: `inv = box_hi + 1pip`.
- `s_struct = |inv - order_px|` = box height + 2 pips (compression =>
  small structural stop); smallest ladder rung `>= s_struct`,
  `>= 10 * c_rt`, `<= 32` pips.
- Target: `tp_mult * S`, `tp_mult = 2.0` (fixed-R).

## Expiry / management

- `v_bars = 3`; `session_cancel = True`; flats as standard; no BE/trail.

## Config grid (20 <= 24 budget)

    S_pips       in {11, 14, 18, 24, 32}
    gen          in {line1_cluster, sd_base}
    box_atr      in {2.5, 4.0}
    fixed: tp_mult=2.0, buf=1.0, v_bars=3, B=12, prox_atr=0.5,
           min_range_atr=0.5, cooldown=12, session eu|us.
