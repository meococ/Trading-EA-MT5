> **FINAL v2 (REVIEW_3 PASS by Lead Ruling 4)**

# MARKET_MECHANICS — the DESIGN atlas (EURUSD/GBPUSD/USDJPY/AUDUSD, 2016–2021, M5)

Preregistration: `STUDY_PLAN.md` sha256 `abc8b5ba…` (ledger T000364);
M4b addendum `STUDY_PLAN_ADDENDUM_M4B.md` (ledger T000392).
**FINAL v2 — REVIEW_3 PASS by Lead Ruling 4.** Numbers below come from
the r2-corrected pipeline: resolver barriers fixed (D25), bootstrap
empty-arm fix (D26), M4/M4b symbol decode (D27), causal grid envelopes
(D28), F-B scope (D29), placebo poke streak-merge (D30).  The
known-answer suite (`tests/`, D32) is green — old code fails it, fixed
code passes 22/22.  Ledger rows: M3 = T000393, M4 = T000397,
M4b = T000395, M5 = T000398 (r2/r2b supersede T000380–387, T000391,
T000394, T000396; pre-review T000367–379 remain historical).

All "D" values are matched-strata contrasts vs placebo (Hajek-weighted,
joint day-block bootstrap B=2000, CI95).  Stability rule: same sign in
≥4/6 years AND ≥3/4 symbols.  "pt" = percentage points of probability.

Detail tables: `RHYTHM.md` (M2), `LEVELS.md` (M3), `BOXES.md` (M4),
`BOXES_M4B.md` (M4b), `LINES.md` (M5), `MOMENTUM.md` (M6).

## What changed vs v1 (pre-review → current, post-REVIEW_2)

| headline | v1 | v2 (corrected) | status | reason |
|---|---|---|---|---|
| S1 bounce premium | +1.50pt | **+2.45pt** | held, stronger | D25 (side=+1 arm was degenerate; true pooled ≈ valid side −1) |
| S2 bounce premium | +1.13pt | **+1.75pt** | held, stronger | D25 |
| PDH/PDL premium | −1.72pt, unstable | **−3.20pt, sig, unstable** | held (negative, not stable) | D25/D26 |
| **ASIA H/L** | −1.01pt, unstable | **−1.43pt, sig+stable** | held (continuation) | D6 lookahead + D25 |
| RND rounds | −2.37pt | +0.29pt ns | void → no effect | D16, D25, D28 |
| Age decay | hl 0.7–2.5h | <3h **+7.3pt**, ~0 by 5h; 8–24h +0.95pt stable | held (sharper) | D25 |
| Touch decay | t1 +4.4→t3+ ≈0 | t1 **+7.3pt**, t2 +1.2pt, t3+ ≈0 | held (stronger) | D25/D26 |
| Retest/role-reversal | no effect | +0.4pt ns, all ns | held | D25/D26/D29 |
| Round cascades | +0.28 ABR, underpowered | +0.135 ABR @h12, ns | held (inconclusive) | D25/D28 |
| Box heights | cluster 27–33p | spread 12–35p | held | D9 |
| Breakout follow-through | −0.067 ABR @h12 | race24 **+1.14pt, stable** (M4b) | void→weak positive | T000392 arm IN |
| Deep-poke → opp edge | +13.8pt | −7.4pt shallow bin, unstable (M4b) | void→contradicts | D22/T000392 |
| **F-TL 3rd touch** | −13.7pt | **+7.16pt** stable | FLIPPED (survives r2) | D11; D26 re-verified |
| Line slope class | no effect | no effect | held | D12/D13/D19 |
| M5 lag-1 autocorr | −0.03…−0.07 | same (M6 unaffected) | held | — |
| VR(12) | LATE 0.53–0.71 | 0.90–0.97 | held (corrected scale) | D21 |
| Pullback depth | median frac 1.00 | 1.00 | held | — |
| EMA25 | not special | not special | held | D14 |
| Strata/statistics | pooled edges | per-symbol edges + fixed bootstrap/decode | corrected | D15/D23/D26/D27 |

---

## Q-R — Do causal swing levels attract reversals beyond placebo?

**Claim tested:** swing levels act as S/R zones; the raw ~64% bounce
rate is generic M5 mean reversion (post-F1: raw P(bounce x1) ≈ 0.64 on
*both* sides, real and placebo — the old 98% arm was the resolver bug).

| set | D x1 | CI95 | q | stable |
|---|---|---|---|---|
| S1 (θ=1·ABR pivots) | **+2.45pt** | +1.81..+2.73 | 0.0015 | YES (6/6y, 4/4s) |
| S2 (θ=2.5·ABR) | **+1.75pt** | +1.09..+2.03 | 0.0015 | YES |
| prior-day H/L | **−3.20pt** | −5.43..−1.23 | 0.0024 | no (years alternate) |
| Asian H/L | **−1.43pt** | −2.77..−0.13 | 0.051 | YES (borderline q) |
| 00/50 rounds | +0.29pt | −1.13..+1.50 | 0.90 | no |

x2: S1 +1.78pt, S2 +1.55pt stable; PDHPDL −2.63pt sig-unstable;
ASIA −0.38pt ns; RND ns.

**Verdict:** *supports* causal pivot levels — the true premium is
~2pt, roughly double the corrupted pre-review estimate.  PDH/PDL and
ASIA H/L attract *continuation* (negative D = break more likely than
bounce); ASIA's effect is small but sign-stable.  Rounds: no effect.

## Q-O — How wide is the zone?  (overshoot quantiles, descriptive)

Overshoot = penetration beyond the zone's far edge before the x1
reversal, from the first M1 bar after zone intersection (D4).

- Bounce overshoot: p50 ≈ 0 everywhere; p75 ≈ 0.2–0.7 pips;
  **p90 ≈ 0.6–0.65·ABR pooled** (≈1.4–3.5 pips by symbol).
- The declared tolerance `max(1p, 0.25·ABR)` sits around p75–p90.

**Verdict:** *supports* "S/R is a small zone"; half-width
≈0.25–0.35·ABR remains empirically right.

## Q-A — Do levels decay with age?

D(x1) vs level age, S1+S2 pooled:

| age | D | q | stable |
|---|---|---|---|
| <3h | **+7.32pt** | 0.0025 | YES |
| 3–8h | +0.47pt | 1.00 | no |
| 8–24h | +0.95pt | 0.0025 | YES (small) |
| 1–3d, 3–5d | nan | — | not identified (day-scoped placebo) |

**Verdict:** *supports* strong perishability — the premium concentrates
in the first ~3h and is near zero by ~5h; a small residual survives
into 8–24h.  Half-life ≈1h on the corrected bins.

## Q-T — Do repeated touches weaken the level?

Pooled {S1,S2,PDHPDL,ASIA}, x1:

| touch | D | q | stable |
|---|---|---|---|
| 1st | **+7.32pt** | 0.0015 | YES |
| 2nd | **+1.24pt** | 0.004 | YES |
| 3rd+ | +0.31pt | 0.995 | no |

x2 same pattern (t1 +4.76pt, t2 +0.99pt; t3+ ns).

**Verdict:** *supports* level consumption — first touch carries the
premium; by the third touch a level is indistinguishable from random.

## Q-B — After a clean break: retest and role reversal?

P(retest ≤12/48 bars) and P(rebound in break direction | retest),
pooled over {S1,S2,PDHPDL,ASIA}: **all contrasts ns** (retest12
D=+0.39pt p=0.58; retest48 +0.09pt; role_rev ≈ 0pt, p≈0.7).

**Verdict:** *no measurable effect* — "old support becomes resistance"
is not detectable above placebo at M5 resolution on DESIGN.

## Q-C — Round-number cascades (Osler 2005)

*(Scope caveat D5: grid columns cover day_open ±3.5·ABR only; D28:
envelope now sized by causal day-open ABR.)*

Declared tests h∈{3,12}, RND vs PRND20 and vs PRAND: all ns
(h12 vs PRAND D=+0.135 ABR, CI −0.06..+0.32, sign-stable but ns).

**Verdict:** *inconclusive* — weakly positive but underpowered
(n≈600–800 crosses/symbol vs ~1.4–2k placebo).

## Q-BO — Box breakouts: follow-through and buildup?

Declared estimator race24, real breaks vs declared P-RAND fake edges:
D=−2.6pt, CI −12.1..+1.5, p=0.20 — **still not identified** (≈48 fake
breaks/symbol; traversal heights ~0.2·ABR vs real ~5·ABR, D22/D30).
buildup−none D=−1.35pt ns.

**M4b addendum (Arm IN interior-level placebo):** race24
**D=+1.14pt, CI +0.44..+1.70, p=0.003, q=0.0075, stable=YES** — real
edge breaks follow through *more* than crossings of a non-structural
interior level at the same traversal distance.  First positive
breakout effect that survives matching — an addendum result under a
redesigned placebo, cleared by REVIEW_3; modest in size, so keep the
caveat that the P-SHIFT placebo is a design choice, not the truth.

**Verdict:** declared arm unidentified; addendum arm weakly supports
breakout follow-through.

## Q-FB — Failed pokes: run to the opposite edge?

Real descriptives: median poke depth ≈ 0.8–1.0 pip; P(reach opposite
edge ≤24 bars) ≈ 0.20–0.23; P(convert to break ≤3 bars) ≈ 0.34–0.36.

Declared P-RAND arm remains **not identified** (D22/D30: sparse,
non-overlapping heights; the deep negative D is mechanical).  M4b
P-SHIFT: shallow pokes (0,1]p traverse **−7.4pt vs placebo**
(p=0.001, q=0.005 — sign-unstable across years → no claim); deeper bins
thin.  A real failed poke is *less* likely to run to the other side
than the same-distance traversal from a non-structural edge.
"+13.8pt deep-poke" remains **voided**.

**Verdict:** *contradicts* the failed-break lore directionally, but
unstable → descriptive only.

## Q-TL — Third touches on causal trend lines

D = P(bounce|real θ2-pivot line) − P(bounce|shifted-copy placebo),
touch ordinal 3+:

| test | D | CI95 | q | stable |
|---|---|---|---|---|
| x1 | **+7.16pt** | +6.47..+7.86 | 0.001 | YES (6/6y, 4/4s) |
| x2 | **+8.39pt** | +7.77..+8.99 | 0.001 | YES |

**Verdict:** *supports* — unchanged through the r2 bootstrap fix:
a third+ touch on a real pivot line bounces ~7–8pt more often than the
same geometry floating in space.  Anchoring on causal pivots carries
real information.

## Q-SLOPE — Does slope class change post-break behaviour?

continuation-24 after break, rising vs rest, real-vs-real:
up-breaks D=−0.99pt (p=0.077, q=0.103 — just misses FDR); down-breaks
+0.21pt ns.  Per-class real-vs-placebo fwd48: mildly negative, no class
separation.

**Verdict:** *no effect.*

## Q-M — M5 momentum structure

- Lag-1 autocorrelation ≈ **−0.03…−0.07**, significant in nearly every
  session×symbol cell.
- VR(12)−1 significantly negative ASIA/EU; corrected VR(12) ≈ 0.90–0.97.
- θ2-leg pullbacks: median retrace = **1.00** of the prior leg
  (p25 0.67, p75 1.48); median depth ≈ 4.1 ABR.

**Verdict:** *supports* mildly mean-reverting M5 — the ~64% raw bounce
baseline engine.

## Q-EMA — Is EMA25 special?

P(|θ1 counter-pivot − EMA_L| ≤ x·ABR), L∈{15,20,25,35,50}: smooth
monotone decline in L; **no kink at L=25**.  Formal differences are
mechanical (shorter MAs sit closer).

**Verdict:** *contradicts* "EMA25 is special".

## Q-SESS — Rhythm facts feeding session boxes / news windows / chop

- Spike (>3·ABR) clusters: **08:00 (8.9%) and 09:00 (9.0%) CET**,
  14:00–15:00 (3.9%), small 02:00 (Tokyo).
- Asia range (00:00–08:00 CET): median **22.6p EURUSD / ~31–32p others**.
- Daily range: median 70p EURUSD / 100p GBPUSD / 67p USDJPY / 59p AUDUSD;
  ≤60p share = 36%/9%/41%/52% — a single 60-pip threshold is
  symbol-sensitive.

---

## Detector / design caveats (for the reviewer)

- M4 declared P-RAND placebo remains underpowered; F-BO/F-FB on that
  arm are reported as unidentified, not as effects (D22/D30).
- M4b Arm-OUT fake pokes are conditioned on excursions deeper than
  ordinary real pokes — the directional fb(0,1] result is descriptive,
  not a stable causal claim (disclosed in `BOXES_M4B.md`).
- F-A bins >24h unidentified under the day-scoped P-RAND placebo.
- Round-number and cascade results cover only grid levels near the
  day open (D5), sized by causal day-open ABR (D28).
- M3 S1 is dense by design (~1.05M touches/symbol); contrasts are
  matched, so density shifts level the field.
