# SF01 / F1 — ZONE REJECTION — a priori spec v2

Frozen before any outcome computation. Any rule change requires a new spec
version + new ledger hash. ENGINE semantics are the frozen referee
(`pa_fill`); per-entry SL/TP prices are NOT expressible there, so structural
geometry is enforced as signal gates + the S ladder (see MAPPING, D1).

## Rationale

A zone that has been touched before and is currently "armed" (actionable in
the perception layer) marks a level other traders watch. When price probes
the band and the probe bar CLOSES BACK OUTSIDE the band, the probe was
absorbed — the market tested and rejected. We trade the rejection toward
the opposite side of the range. The matched-random baseline enters at the
same time-of-day/week/month cells with identical S/tp geometry, so a
positive lift means the zone+rejection event itself carries information.

## Causal inputs (all known at close of M5 bar t)

From `families/sf_ctx` cache for `(symbol, gen)`:

- `zones_at(t)`: live zones within 3.5xATR(H1) of close, strongest first,
  with `armed`, `broken`, `approach_side`, `touches`, band `[lo, hi]`.
- `atr_m5[t]`; `first_live_idx` / `warmup` (no signals on warmup bars).

## Signal rules (bar t)

1. Pick the FIRST zone in `zones_at(t)` (strongest-first) satisfying:
   - `armed == 1`, `broken == 0`, `approach_side != 0`,
     `touches >= touches_min` (=1).
2. Probe + rejection on bar t:
   - ceiling (`approach_side == -1`, price arrived from below):
     `h[t] >= z.lo` AND `c[t] < z.lo` (closed back below the band);
   - floor (`approach_side == +1`, price arrived from above):
     `l[t] <= z.hi` AND `c[t] > z.hi`;
   - approach-side gate: `c[t-1] <= z.hi` (ceiling) / `c[t-1] >= z.lo`
     (floor) — the previous close is not beyond the far band edge; this
     admits 2-bar rejections where bar t-1 closes inside the band
     (Lead Review 2: formula is the pre-registered rule; wording amended);
   - if `rej_body == 1`: `c[t] < o[t]` (ceiling) / `c[t] > o[t]` (floor);
   - bar range gate: `h[t] - l[t] >= 0.5 * atr_m5[t]`.
3. `side`: ceiling rejection -> `-1`; floor rejection -> `+1`.

## Order geometry

- Entry: STOP order beyond the signal bar —
  short: `order_px = l[t] - 1pip`; long: `order_px = h[t] + 1pip`
  (encoded via `order_px`; engine `buf_pips` unused).
- `inv` (pre-fill invalidation): the probe extreme —
  short: `h[t] + 1pip`; long: `l[t] - 1pip`.
- Structural stop distance `s_struct = |inv - order_px|` (= range + 2pip).
- **S ladder** (D1): `LADDER = {11, 14, 18, 24, 32}` pips. A signal is
  emitted into config `S` iff `S` is the smallest rung `>= s_struct` AND
  `s_struct >= 10 * c_rt_pips` (charter 10x-cost guard). Signals with
  `s_struct > 32` pips are skipped. Because each signal lands on exactly one
  rung, configs partition the signal set — no overlap between S configs.
- Target: engine `TP = fill + side * tp_mult * S`, `tp_mult = 2.0` —
  fixed-R target (charter allows "structural or fixed-R"; the
  opposing-structure gate of v1 was removed for cadence, see HISTORY).

## Expiry / management

- Pending validity `v_bars = 3` M5 bars; `session_cancel = True`;
  `daily_flat_hour = 22`, `friday_flat_hour = 20`, `weekend_veto = True`,
  `legacy_flats = False`. No break-even / trailing / scratch / partials.

## Dedupe

- Same `zid` may signal at most once per `cooldown = 12` bars.
- At most one signal per bar (strongest qualifying zone).

## Config grid (20 <= 24 budget; leaves 4)

    S_pips       in {11, 14, 18, 24, 32}   (ladder rung)
    gen          in {line1_cluster, sd_base}
    rej_body     in {0, 1}
    fixed: tp_mult=2.0, buf=1.0, v_bars=3, min_range_atr=0.5,
           touches_min=1, cooldown=12, session/flats defaults.

## MAPPING note (engine constraint)

`pa_fill` realises `SL = fill -/+ S` and `TP = fill +/- tp_mult*S` (fixed-R).
"Stop at structure" is enforced by the ladder rule: the emitted config's
stop is the smallest rung >= the structural distance, so the realised SL
always sits at or just beyond the probe extreme (within ~1.33x). `inv`
carries the structural invalidation pre-fill. The matched-random baseline
inherits identical S/tp/order semantics — geometry-fair comparison.

## HISTORY

- v1 (sha d182310f, ledger T000052): S in {20,30}, `s_min_frac=0.55`,
  opposing-structure gate `d_opp >= tp_mult*S`. Never screened: DESIGN census
  (pre-outcome) showed the fixed window + d_opp gate collapse cadence to
  ~0.36 signals/week basket (EURUSD funnel: 31,377 probe bars -> 2,625
  s_struct-pass -> 64 d_opp-pass). Superseded before any outcome.
- v2: S ladder {11,14,18,24,32} with smallest-rung assignment; d_opp gate
  removed (fixed-R target declared); grid 20 configs.
