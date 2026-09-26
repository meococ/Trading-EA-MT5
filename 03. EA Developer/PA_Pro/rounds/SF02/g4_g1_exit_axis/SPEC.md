# G4 SPEC — g4_g1_exit_axis (v1)

Round: SF02 | TF: M5 | Symbols: EURUSD GBPUSD USDJPY AUDUSD
Base family: g1_htf_pullback v2 (prereg T000282, sha 948b62d2)
Mechanism: identical entry logic to G1 — LIMIT order at the proximal
edge of the single most salient armed zone on the trend-aligned side,
invalidation at the deeper of (zone far edge, pullback extreme).
G4 changes ONLY the exit axis per the mandate ("change only the S and
tp_mult grid, never the entry logic").

## Rules

All entry rules = G1 v2 SPEC verbatim:
- trend: tr = s_tr_<tr_src>[t] in {-1,+1} (tr_src in {h1,h4})
- zone: single most salient armed zone per side, salience = plan
  formula (T000229), salience >= 2.0
- touch: long floor zone, l[t] <= z.hi + 0.35*ATR_M5; short ceiling,
  h[t] >= z.lo - 0.35*ATR_M5
- entry: LIMIT at proximal edge (long z.hi - buf, short z.lo + buf,
  buf = 1 pip), v_bars = 6
- inv: deeper of (zone far edge, pullback extreme) ± buf; pullback leg
  starts after the last bar fully on the approach side, pull_max = 96
- room: nearest opposing armed-salient edge >= 2.0 * S from order_px
- cost guard: s_struct >= 10 * c_rt_pips; smallest ladder rung >= s_struct
- dedupe: one signal per zid per cooldown=12; one/bar
- session: in-session signals only

## Exit axis under test (the only change vs G1)

- S_pips in {18, 55}  (thick rung vs flat-bound wide rung)
- tp_mult in {1.0, 2.0, 3.0}
- engine: order_type=limit, flats=True, daily_flat_hour=22,
  friday_flat_hour=20, weekend_veto=True, invalidation=True,
  session_cancel=True

## Grid — 24 cells <= 24 budget

gen {line1_cluster, sd_base} x tr_src {h1, h4} x S {18, 55} x
tp_mult {1.0, 2.0, 3.0}

## Screen

pa_eval DESIGN, tiers x1/x1.5/x2, PAIRED_RANDOM baseline per DECISIONS D3
(limit randoms: order_px = signal-bar extreme ∓ buf; K=20,
seed=20260921). Same charter section-8 gates as all families.
