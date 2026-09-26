# SF02 — AUTOPSY of SF01 (DESCRIPTIVE unless labelled REFEREE)

Plan: `AUTOPSY_PLAN.md`, ledger prereg T000229 (sha afdcf64f…).
Data: DESIGN 2016–2021 only, via the SF01 zone caches and `pa_fill` fills.
Populations: the exact thick-cell SF01 entries with corrected D9 tags and
their seed-matched randoms (K=20, seed 20260920): F1 12,720 / F2 326 /
F3 8,669 / F4 10,459 / F5 824 / F6 1,474 strategy entries.
Everything under A2–A4 is DESCRIPTIVE (computed outside `pa_eval`, on
referee-simulated trades and DESIGN bars). A1 rows are REFEREE
(`pa_eval`, ledgered); the `exp_r` column was recovered by replaying the
identical deterministic random set through `pa_fill` — PF replayed
matches the ledgered PF to 7 decimals for all 32 cells.

## A1 — random drag curve (REFEREE; N=301,072 per cell)

exp_R (R per trade) / PF of matched-random entries, pooled 4 symbols:

| S_pips | tp=1.0 | tp=1.5 | tp=2.0 | tp=3.0 |
|--------|--------|--------|--------|--------|
| 11 | -0.099 / .814 | -0.094 / .844 | -0.093 / .856 | -0.087 / .874 |
| 14 | -0.075 / .851 | -0.073 / .873 | -0.070 / .885 | -0.066 / .897 |
| 18 | -0.057 / .879 | -0.054 / .898 | -0.053 / .904 | -0.050 / .913 |
| 24 | -0.043 / .900 | -0.042 / .911 | -0.041 / .915 | -0.036 / .928 |
| 32 | -0.032 / .914 | -0.031 / .922 | -0.027 / .934 | -0.026 / .937 |
| 40 | -0.025 / .924 | -0.021 / .938 | -0.020 / .941 | -0.019 / .945 |
| 55 | -0.018 / .930 | -0.016 / .937 | -0.016 / .940 | -0.016 / .940 |
| 75 | -0.013 / .934 | -0.012 / .937 | -0.012 / .939 | -0.013 / .935 |

Questions answered:
- **Random drag falls below 0.03 R only at S >= 40.** At S 11–24 it is
  -0.036 to -0.099 R — every pip of stop below ~40 pays a tax.
- **Intraday flats are the binding constraint.** Exit mix (x1): at
  S=11/tp2, TP+SL resolve 92% of trades; at S=32/tp2 DAILY+FRIDAY+MIDNIGHT
  already 60%; at S=75 DAILY exits alone are 68–73% and TP hits collapse
  to 0.2–7%. Wider geometry does NOT lift random PF above ~0.94 because
  the day-flat truncates TP reach — the trade degenerates to "random
  intraday hold minus cost". No S/tp combination reaches PF 1.0.

## A2 — exit-free entry information (DESCRIPTIVE)

E[MFE]/E[MAE] in ATR(H1) units, capped at the session flat; edge ratio
= E[MFE]/E[MAE]; delta = strategy − random; day-clustered bootstrap CI95.

| family | h6 Δ | h24 Δ | h96 Δ | verdict |
|---|---|---|---|---|
| F1 zone rejection | −0.68 [−.70,−.66] | −0.46 | −0.37 [−.39,−.35] | **adverse** |
| F2 break-retest | −0.48 [−.53,−.28] | −0.34 | −0.33 [−.38,−.12] | **adverse** |
| F3 failed breakout | −0.52 [−.54,−.50] | −0.34 | −0.29 [−.31,−.26] | **adverse** |
| F4 trend pullback | −0.51 [−.53,−.49] | −0.31 | −0.26 [−.29,−.22] | **adverse** |
| F5 second entry | +0.18 | +0.18 [+.08,+.28]* | +0.17 [+.04,+.30] | **informed** |
| F6 volman box | +0.42 [+.30,+.54]* | +0.17 | +0.15 [+.05,+.24] | **informed** |

(*CI95 read from A2_mfemae.json; h6/h24 F5/F6 also positive.)
Randoms sit at edge ≈ 1.00 (symmetric excursions) as expected.
Reading: probe/rejection-style M5 entries are *adversely* informed —
price moves against them more than for them at every horizon; momentum
families F5/F6 DO carry positive directional information that the
intraday-flat exits discarded. Caveat (plan §A2): outcome-conditioned
subsets are not usable as mechanism evidence; these deltas are
entry-information measurements, not exit-conditioned PF.

## A3 — perception audit (DESCRIPTIVE)

Armed-zone density (sampled every 250 M5 bars, pooled symbols):

| generator | zones within ±1×ATR_H1 | within ±2×ATR_H1 |
|---|---|---|
| line1_cluster | 3.28 | 4.60 |
| sd_base | 0.62 | 1.05 |

Median rank (by engine strength) of the triggering zone among armed
zones: F1 2, F2 2, F3 3, F4 2, F6 3 — SF01 typically fired on the
*2nd–3rd* strongest nearby zone, i.e. mid-stack noise.

Lift (pp, Newcombe CI95) by salience tercile of the triggering zone:

| family | lo | mid | hi |
|---|---|---|---|
| F1 | −1.0 [−2.9,+1.0] | −2.0 [−4.0,+0.0] | −0.4 [−2.5,+1.7] |
| F2 | −13.1 [−21.7,−2.2] | +4.0 [−6.9,+15.7] | +6.9 [−4.2,+18.6] |
| F3 | −0.4 [−2.6,+1.8] | +0.6 [−1.6,+2.9] | −1.7 [−3.9,+0.5] |
| F4 | −0.4 [−2.4,+1.6] | +0.5 [−1.6,+2.5] | −0.5 [−2.5,+1.6] |
| F6 | −1.4 [−5.8,+3.3] | +2.3 [−2.3,+6.9] | −4.8 [−9.2,−0.3] |

Reading: salience terciles do NOT monotonically rescue lift — F1/F3/F4
stay ~0/negative at every tercile; F6's positive slice is mid-tercile
while its hi-tercile is the worst. Salience alone does not explain the
edge; sparsity of the generator (sd_base ≈ 1 armed zone near price) is
the more actionable perception fix.

## A4 — context slices (DESCRIPTIVE)

BH correction over the whole plan: **152 tests, 33 significant at 5%**
(includes the 30 A2 deltas above, which dominate the count). All bins
reported in `A4_slices.json`; the load-bearing non-A2 survivors:

- `atr_regime = high` (ATR_H1 top tercile) hurts: F1 −2.67pp
  [−4.1,−1.3] N=4,692; F4 −2.81pp [−4.7,−0.9] N=2,561; F5 −7.82pp
  [−12.8,−2.2] N=288 (all BH-sig). High-vol regimes destroy probe-type
  entries — cost of being wrong is larger than the edge.
- F4 `tr_h4 = counter` (pullback entries taken against the H4 trend):
  lift +3.45pp [+0.02,+7.0] N=821 — positive but only marginal under BH.
- `room_R >= 2` does NOT rescue: F1 ge2R −4.7pp, F4 ge2R −5.5pp,
  F3 1to2R −2.7pp — "room to opposing structure" slices were sparse
  (N 37–1,109) and if anything worse.
- `chase` terciles (entry distance from zone edge, ATR_M5): no clean
  monotone story — F1 worst at mid chase (−2.2pp), F6 worst at mid
  (−2.9pp); F6 far chase positive (+0.2). The Lead's chase hypothesis is
  confirmed as *an* F4 defect (thrust-bar entries ~12p past the zone)
  but distance alone does not separate winners.
- `h4_pos` (discount/premium in the rolling H4 range): F3 discount
  −1.3pp [−3.4,+0.8]; F4 discount −0.9pp — weak, not BH-significant.

## Total slice/test count

152 hypothesis tests corrected by BH (30 A2 edge deltas + 15 A3 tercile
lifts + 107 A4 bin lifts). A1 contributes 32 drag-curve cells
(descriptive curve, not lift tests). A3 density/rank are descriptive
measurements, not tests.

## Ranked hypotheses (≤4)

**H1 — Momentum continuation carries real information; probe/rejection
does not.** Mechanism: second-entry and build-up break entries sit at
the *start* of order-flow continuation (trapped-countertrend fuel), so
MFE>MAE vs random (+0.15..+0.42 edge delta, BH-significant at h24–96);
zone-probe bars sit at liquidity grabs where the move continues through
(edge delta −0.26..−0.68). Slices: all A2 rows; corroborated by F6's
positive-lift sd_base cells in the SF01 screen. Falsifiable sketch
(=G1/G3): enter WITH the HTF trend at a salient level via limit-at-edge
(G1) or compressed-build-up break (G3); predict positive exit-free edge
*and* positive screen lift. Kill criterion: lift CI <= 0 on the thick
cells.

**H2 — Wide-S cells need a multi-day horizon; the day-flat is the drag.**
Mechanism: at S ≥ 32 the random baseline's TP almost never arrives
inside the session-day (TP exits < 10% at S=32/tp≥2, < 1% at S=75);
DAILY/FRIDAY flats resolve the trade at market — expected value =
drift-minus-cost ≈ −0.01..−0.03 R regardless of entry quality. Slices:
A1 exit-mix columns; A2 shows F5/F6 MFE still growing at h48–96 — beyond
the flat. Falsifiable sketch: G4 exit-axis variant — same entries, S on
{24,32,40,55} with tp_mult ∈ {1.5,2,3}; predicts flat-limited PF ~0.93
unless the referee supports multi-day holding (→ Q4 proposal).

**H3 — Perception: generator sparsity beats salience rank.** Mechanism:
with 4.6 armed zones within ±2×ATR_H1 (line1_cluster) "at a zone" is a
coin flip; sd_base yields ~1 zone near price — a real filter. Salience
terciles do not order lift (H-vs-lo differences ≈ 0 or negative), so
the fix is *fewer zones*, not a better score on many zones. Slices: A3
density table; A3 tercile lifts. Falsifiable sketch: G1/G2/G3 restrict
to the single most salient armed zone per side AND read sd_base cells
separately; predicts sd_base cells ≥ line1 cells on lift.

**H4 — High-ATR regimes are toxic to probe entries.** Mechanism: in
top-tercile ATR_H1 the adverse excursion of a zone touch exceeds the
edge (wicks run further than the rejection). Slices: A4 atr_regime/high
F1 −2.7pp, F4 −2.8pp, F5 −7.8pp (BH-sig). Falsifiable sketch: any
family could gate ATR regime — but this is a rescue-flavoured filter,
so it stays a *hypothesis for a future family* (e.g. momentum families
only in mid/low ATR), not a retro-fit.

DESIGN is now seen for these slices; DESIGN screens of these hypotheses
are optimistic; promotion requires CONFIRM, opened once by the Lead.

## What this chose for SF02 (feed into DECISIONS)

- G1 (HTF pullback at salient edge, limit order) — targets H1+H3.
- G3 (build-up break, episode model) — targets H1 (F6 momentum hint).
- G2 as a *pure* salient-zone rejection family is deprioritised: A2 says
  probe/rejection entries are adversely informed — a salience-only fix
  does not address the adverse edge. If run, it should be the
  trap-of-the-trap variant (trade WITH the failure of the rejection),
  not a re-run of F1 at sparser zones.
- G4 exit-axis variant — targets H2; only meaningful if paired with a
  momentum entry (G1/G3 winner).

## Addendum — A2 anchor verification (Lead Review 2 request, 07:25Z)

Hand-checked 10 F1 trades (EURUSD, S18/line1, first 400 signals ->
210 fills via pa_fill.simulate, tier x1):

- ANCHOR: autopsy used e["order_px"] = the stop level; in all 10 trades
  fill_raw == stop exactly (no M1 gaps). Anchor equals fill price.
- SIDE SIGN: shorts gain when price falls (r=+2 on TP below fill),
  longs the mirror. Correct.
- WINDOW: autopsy window starts at sig+1; fills arrive 1-4 bars later,
  so ~1-4 pre-fill bars enter MFE/MAE. Recomputed from fill_bar+1
  anchored at fill_raw: per-trade shifts are +-0.1..0.3 ATR_H1 and
  bidirectional (pre-fill window adds favorable AND adverse excursion
  roughly symmetrically). Cannot explain a 0.32-vs-1.00 edge-ratio gap.

VERDICT: the A2 anomaly stands — F1-style stop entries placed after
strong bars buy into genuine short-term mean reversion; the adverse
edge ratio is a property of the entry style, not an artefact.

## A2-verification — F6 addendum (07:55Z)

Same hand-check on F6 (EURUSD, S24/line1/box4.0 — its densest screened
cell; 361 signals -> 357 fills):

- SIDE SIGN: correct (shorts gain on falls, longs on rises).
- ANCHOR: unlike F1, F6 entries carry no `order_px` (default stop =
  signal extreme ± buf). The autopsy therefore anchored MFE/MAE at
  `c[sig]` — the signal CLOSE, not the fill price. Real fill =
  fill_raw ≈ stop + occasional M1-open gap slippage (e.g. stop 1.07375
  filled 1.07390). The offset is ~1-4 pips ≈ 0.03-0.15 ATR(H1),
  systematically applied to BOTH strategy and matched-random cohorts
  (randoms were anchored the same way), so the strategy-minus-random
  deltas largely cancel it. MFE/MAE absolute levels are slightly
  inflated for both cohorts; the edge-ratio DELTA and its sign stand.
- WINDOW: fills arrive ~1 bar after sig, so the pre-fill overlap is
  minimal for F6.

CONCLUSION: A2 findings hold — F1-style adverse entry edge is real
(verified anchor + sign), and F5/F6 positive edge survives the
anchor correction (bias symmetric across cohorts). Known small flaw
for any rerun: anchor should be fill_raw when order_px is absent.
