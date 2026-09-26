# SF02 / G1 — HTF-STRUCTURE PULLBACK AT A SALIENT ZONE — a priori spec v2

Frozen before any outcome computation. Any rule change requires a new spec
version + new ledger hash. ENGINE semantics are the frozen referee
(`pa_fill`); structural geometry is enforced as signal gates + the S ladder
(D1 convention, wider rungs — blueprint §8 rung 2).

## Rationale (from SF01 autopsy, DESCRIPTIVE)

SF01 showed two concrete defects (Lead QA): (i) up to 6 armed zones within
+-2xATR(H1) make "price is at a zone" nearly always true, and (ii) the
F4-type trigger chases — entry ~12 pips beyond the zone after a thrust bar.
G1 fixes both: only the SINGLE most salient armed zone per side may
trigger, and the entry is a LIMIT order AT the zone edge — it fills only
if price returns to the level, never beyond it.

Mechanism: in an HTF trend, a pullback into a salient floor/ceiling zone
that holds (signal bar does not close through the far edge) marks
absorption at a level other traders watch. Buying the edge (not the
thrust) gives entry at structure with a real invalidation behind the band.

## Causal inputs (all known at close of M5 bar t)

From `families/sf_ctx` cache for `(symbol, gen)`:

- `zones_at(t)`: live zones within 3.5xATR(H1), strongest first, with
  `armed`, `approach_side`, band `[lo, hi]`, `n_respected`, `age`, `zid`.
- `s_atr_m5[t]`, `s_atr_h1[t]`; `s_tr_h1[t]`, `s_tr_h4[t]` (HTF trend sign).
- `first_live_idx` / `warmup` — no signals on warmup bars.
- Salience: the AUTOPSY_PLAN-fixed causal formula (ledger T000229):
  `1.0*n_respected + 1.0*pivot_confluence + 0.5*round_confluence
   - 0.5*(width/ATR_H1) + 0.25*log1p(age/96)`.

## Signal rules (bar t)

1. Trend gate: `tr = s_tr_<tr_src>[t]` in {-1,+1} (tr_src in {h1,h4}).
2. Zone gate: among armed zones with `approach_side == tr`
   (uptrend -> floor zones approached from above; downtrend -> ceiling),
   pick the single highest salience `s >= sal_min` (=2.0).
3. Touch gate (pullback reached the proximal edge):
   - long (floor, approached from above): `l[t] <= z.hi + touch_atr*ATR_M5`;
   - short (ceiling, approached from below): `h[t] >= z.lo - touch_atr*ATR_M5`.
4. Zone-holds gate: long `c[t] >= z.lo`; short `c[t] <= z.hi`
   (the bar must NOT close through the far edge).
5. Bar range gate: `h[t]-l[t] >= min_range_atr * ATR_M5` (0.3).

## Order geometry

- Entry: LIMIT order at the proximal edge —
  long `order_px = z.hi - 1pip`; short `order_px = z.lo + 1pip`.
- `inv` (pre-fill invalidation): the DEEPER of the zone's far edge and
  the pullback extreme —
  long `inv = min(z.lo, pull_low) - 1pip`;
  short `inv = max(z.hi, pull_high) + 1pip`,
  where the pullback leg starts just after the last bar `j <= t` lying
  FULLY on the approach side of the zone (long: `l[j] > z.hi +
  touch_atr*A5`; short: `h[j] < z.lo - touch_atr*A5`), searched causally
  backward and capped at `pull_max = 96` bars (full window if none found).
  `pull_low = min(l[j+1..t])`, `pull_high = max(h[j+1..t])` — the swing
  extreme the pullback retraced from, so `inv` sits beyond the real apex,
  not merely behind the band.
- `s_struct = |order_px - inv|` — zone width plus pullback depth; populates
  the wider rungs the mandate asks for.
- **No-chase guard**: order must sit within `touch_atr*ATR_M5` of `c[t]`
  (long: `order_px <= c[t] + touch_atr*A5`; short mirrored). Combined
  with the touch gate this bounds entry distance from the edge.
- **Room gate**: distance from `order_px` to the nearest opposing
  armed+salient zone edge must be `>= room_min_R * S` (2R); if no
  opposing zone exists the gate passes (infinite room).
- **S ladder** (wider rungs): `LADDER = {18, 24, 32, 40, 55}` pips.
  Signal emitted into config `S` iff `S` is the smallest rung >= s_struct
  AND `s_struct >= 10 * c_rt_pips`. `s_struct > 55` skipped. Configs
  partition the signal set (no overlap).
- Target: engine fixed `TP = fill + side * tp_mult * S`, `tp_mult = 2.0`.

## Expiry / management

- Pending validity `v_bars = 6` M5 bars; `session_cancel = True`;
  `daily_flat_hour = 22`, `friday_flat_hour = 20`, `weekend_veto = True`,
  `legacy_flats = False`. No break-even / trailing / scratch / partials.
- Session gate (D3): signal bar must close in EU (05:00-11:00 UTC) or
  US (11:30-17:30 UTC) session.

## Dedupe

- Same `zid` at most once per `cooldown = 12` bars; one signal per bar;
  global cooldown 12 bars.

## Config grid (20 <= 24 budget)

    S_pips   in {18, 24, 32, 40, 55}     (ladder rung)
    gen      in {line1_cluster, sd_base}
    tr_src   in {h1, h4}
    fixed: tp_mult=2.0, buf=1.0, v_bars=6, touch_atr=0.35,
           sal_min=2.0, room_min_R=2.0, min_range_atr=0.3,
           cooldown=12, session=1.

## MAPPING note (engine constraint)

`pa_fill` realises `SL = fill -/+ S` and `TP = fill +/- tp_mult*S`
(fixed-R). The LIMIT order means the fill is AT the zone edge (or better
via gap); the realised SL sits at or just beyond the zone's far edge
(within ~1.3x). `inv` carries structural invalidation pre-fill.
Matched-random baseline inherits identical S/tp/limit semantics.

## HISTORY

- v1 (sha ed2d634a, ledger T000279): `inv` at the zone's far edge only.
  Never screened: the DESIGN census (pre-outcome, no outcome fields)
  showed s_struct = zone width + 2p collapses the ladder — ~97% of
  signals on rung 18, 16/20 cells empty (g1_htf_pullback/CENSUS.json).
- v2 (DECISIONS D1): `inv` = deeper of (far edge, pullback extreme) —
  "stop below the pullback low"; populates the 24-55p rungs the mandate
  requires. New ledger hash; v1 superseded pre-outcome.
