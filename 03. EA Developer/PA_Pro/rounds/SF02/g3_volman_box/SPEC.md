# SF02 / G3 — VOLMAN BUILD-UP BREAK, PROPER BOX — a priori spec v2

Frozen before any outcome computation. Any rule change requires a new spec
version + new ledger hash. ENGINE semantics are the frozen referee
(`pa_fill`); structural geometry enforced as signal gates + the S ladder.

## Rationale

SF01-F6 died for two reasons: (a) the box test (`range <= box_atr*ATR`)
admitted spike-and-fade clusters, not real compression; (b) zone perception
was unfiltered. The F6 `sd_base` cells carried the only positive-lift hint
of SF01 (+14.6pp CI [+3.1,+26.1] at N=77 — thin but directional).

G3 rebuilds it properly (Volman "build-up"): a genuinely compressed box —
12-bar range at or below its own rolling 10-20th percentile AND mean body
at most 0.5xATR(M5) — pressed against a SALIENT zone, broken WITH the HTF
trend via a stop order beyond the box edge.

## Causal inputs (all known at close of M5 bar t)

From `families/sf_ctx` cache for `(symbol, gen)`:

- `zones_at(t)` armed zones with `approach_side`, band `[lo, hi]`,
  `n_respected`, `age`, `zid`.
- `s_atr_m5[t]`, `s_atr_h1[t]`; `s_tr_h4[t]` (trend source fixed h4).
- Salience = AUTOPSY_PLAN formula (ledger T000229), `>= sal_min` (2.0).
- `first_live_idx` / `warmup` — no signals on warmup bars.

## Signal rules (bar t)

1. Compression episode: a bar `j` is compressed when the 12-bar window
   `[j-12, j-1]` satisfies BOTH `box_rng <= pct_max`-th percentile of
   rolling 12-bar ranges over the preceding `W_pct = 576` bars AND
   `mean|c-o| <= 0.5 * ATR_M5`. Contiguous compressed bars (at most
   `CMAX = 24`) form the build-up cluster; the cluster's box edges are
   `max(h)/min(l)` over `[jstart-11, jend]`.
2. Zone gate (evaluated on each compression bar): an armed zone with
   `salience >= 2.0` whose EITHER edge lies within `prox_atr*ATR_M5`
   (1.0) of the cluster edge on the break side — ceiling
   (`approach_side == -1`) arms a long episode, floor (`+1`) arms a
   short episode. The episode expires `E = 6` bars after the last
   compression bar.
3. Trend + trigger on bar t: `tr = s_tr_h4[t]` in {-1,+1} selects the
   armed episode on that side; trigger = `c[t]` beyond the cluster edge
   + 1 pip (up: `c[t] > hi + buf`; down: `c[t] < lo - buf`), and the
   trigger bar range `>= 0.3 * ATR_M5`.

## Order geometry

- Entry: STOP order beyond the cluster edge — up `order_px = hi + 1pip`;
  down `order_px = lo - 1pip`.
- `inv`: far side of the cluster — up `lo - 1pip`; down `hi + 1pip`.
- `s_struct = |order_px - inv|` = cluster height + 2 pips.
- **S ladder**: `LADDER = {11, 14, 18, 24, 32}` pips (boxes are tight —
  rung-1 stops; rung-2 geometry lives in the percentile test, not S).
  Signal emitted into config `S` iff smallest rung >= s_struct and
  `s_struct >= 10 * c_rt_pips`.
- Target: engine fixed `TP = fill + side * tp_mult * S`, `tp_mult = 2.0`.

## Expiry / management

- `v_bars = 3` M5 bars; `session_cancel = True`; `daily_flat_hour = 22`,
  `friday_flat_hour = 20`, `weekend_veto = True`, `legacy_flats = False`.
- Session gate (D3): EU 05:00-11:00 / US 11:30-17:30 UTC.
- Percentile needs `t >= W_pct + B` bars of history — bars failing this
  are skipped (a warm-up effect, not a data filter).

## Dedupe

- Same `zid` at most once per `cooldown = 12` bars; one signal per bar.

## Config grid (20 <= 24 budget)

    S_pips   in {11, 14, 18, 24, 32}
    gen      in {line1_cluster, sd_base}
    pct_max  in {10.0, 20.0}
    fixed: tp_mult=2.0, buf=1.0, v_bars=3, B=12, W_pct=576,
           body_max_atr=0.5, prox_atr=1.0, sal_min=2.0,
           min_range_atr=0.3, cooldown=12, session=1, tr_src=h4,
           CMAX=24, E=6.

## HISTORY

- v1 (sha 8cdc8f21, ledger T000280): single-bar coincidence — compression
  AND break through the zone's far edge on the same bar, prox 0.5xATR.
  Never screened: DESIGN census (pre-outcome) returned ~0.05
  signals/week — the joint event is near-nonexistent (EURUSD funnel:
  7,351 compressed trend bars -> 258 aligned breaks -> 3 zone-gate
  passes).
- v2 (DECISIONS D2): episode semantics — the build-up is a contiguous
  compressed cluster (<=24 bars); the break may lag the last compressed
  bar by up to E=6 bars; the zone gate is evaluated on compression bars;
  `inv` = far side of the cluster. New ledger hash; v1 superseded
  pre-outcome.

## MAPPING note

`pa_fill` realises fixed `S`/`tp_mult*S`. The stop order fills beyond the
box edge; realised SL sits at or just beyond the far box edge (within
~1.3x). `inv` carries structural invalidation pre-fill. Matched-random
baseline inherits identical semantics.
