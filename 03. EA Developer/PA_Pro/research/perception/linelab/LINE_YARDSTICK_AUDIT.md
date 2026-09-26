# LINE_YARDSTICK_AUDIT — L1: how trustworthy are the golden line labels?

2026-09-21, lane LINE-LAB.  Method: `linelab/audit_lines.py` measures
every TUNE-v2 PATTERN_LINE against its own day's BOOK M5 bars only
(book text parsed for side/anchors via `golden/textfeat.py`; no engine
output read).  Data: `linelab/audit_lines.json`; renders:
`linelab/audit_png/` (10 per stratum, seed 20260921, audited line
thickened + tagged "AUDIT").

## What the labels ARE (read before the numbers)

All 198 are `prec=eye`; 184 `repaired`, 12 `unusable`, 2 `time_only`.
The repairer (`golden/repair.py:fit_line`) does NOT transcribe pixels —
it *searches* extreme pairs / anchor rays on the span maximising
`touches − 1.5·close-violations` under the clause's slope bounds, side
and named anchors (anchor pin tolerance 2p).  Consequences:

- **price0/price1 are fitted geometry, not observed ink.**  They are
  the best bar-fit consistent with the text, not the author's pixels.
- **t1 is where ink stops, not an anchor.**  Broken/extended lines
  keep their drawn span past the break (refit on pre-break prefix,
  span unchanged).  Expect large end1-to-extreme residuals by design.
- `MIN_TOUCHES≥2` was enforced only when the clause gives a side
  (repair.py:277 `if f["side"] and tch < MIN_TOUCHES`); 76 of 122
  constrained-fit lines have no side word → no floor applied.

## (a) Reliability per stratum

| stratum | n | hug4_dev p50/p90 (p) | anchor_res p50/p90 | touches@1.5≥2 | suspects |
|---|---|---|---|---|---|
| text_anchor_bars | 62 | 0.25 / 2.03 | 0.0 / 1.84 | 95% | 6 |
| constrained_fit | 122 | 0.70 / 5.97 | — | 74% | 38 |
| constrained_fit+fail | 1 | 0.83 | — | 100% | 0 |
| unusable / time_only | 13 | not scorable (no span/endpoints) | | | |

- **text_anchor_bars: reliable at the anchor.**  Median anchor
  residual 0 p, p90 1.84 p — the pin contract holds empirically.
  The free end is fit-quality, not pinned (end1 p90 ≈ 32 p).
- **constrained_fit: mixed.**  Core fits hug within ~0.7 p, but ~26%
  have <2 touches even at 2.0 p — a *slope through a region*, not a
  defended line; concentrated where the clause gives no side word.
- **Endpoints ≠ anchors.**  end0 p50 ≈ 0–0.6 p (t0 usually IS an
  anchor); end1 p50 0.7–2.3 p but p90 20–32 p (t1 is ink end).
- Visual check of the 20 rendered samples: good labels hug a run of
  same-side extremes and continue past the break (e.g. 9.15a, 9.21a);
  bad ones are steep rays that cross price after 1–2 touches
  (9.66c#2) or sit in dead space (9.3a, 9.49b).

## (b) Suspect list — proposals only, yardstick stays frozen

Tier A — geometry not trustworthy (44 objects):
`thin_touch` (<2 touches @2.0p; 33), `loose_fit` (hug4>4p; 27),
`anchor_drift` (named anchor >3p off; 4), `side_mismatch` (3),
`slope_sign` (2).  Both R3 spot-check misses land here:
9.41a#0 (side_mismatch — text says "falling line from the ~08:20
high" inside a bull flag; label hugs lows), 9.66c#5 (all three).

    9.3a#0 9.7b#1 9.9a#0 9.10b#0 9.10c#0 9.12a#0 9.12a#1 9.14b#1
    9.14b#4 9.14c#1 9.17c#2 9.18a#2 9.18c#1 9.18c#3 9.19a#4 9.19b#1
    9.19b#3 9.20b#2 9.21b#1 9.21c#0 9.23a#4 9.23b#1 9.26a#1 9.29a#2
    9.30a#1 9.31b#2 9.31b#3 9.31c#0 9.33b#1 9.33b#2 9.36c#2 9.37c#3
    9.37c#4 9.40a#1 9.41a#0 9.48b#2 9.53a#1 9.58b#0 9.58c#0 9.59b#1
    9.4a#3 9.4a#5 9.64b#1 9.66c#5

Tier B — defended run ends early; t1 is narrative (9 objects;
`early_fade`: last touch <50% of span, span>60min):

    9.58b#0 9.23b#1 9.66c#2 9.33b#2 9.41a#0 9.61b#1 9.6c#1 9.51b#1
    9.4b#1

## (c) Supported tolerance

Measured on the trusted subset (n=141):

| where | supported σ | basis |
|---|---|---|
| named anchor bar | **≤1.5 p** | anchor_res p90 1.06 p |
| hugged extremes mid-span | **~2 p** | hug4_dev p95 = 2.0 p |
| unanchored t0 | ~3–6 p | end0_res p90 = 6.2 p |
| t1 endpoint | **unreliable** | end1_res p90 ≈ 20 p — evaluate by span overlap + mid-span price, never endpoint distance |
| time | ±10 min (catalogue read) | common.py TIME_SIGMA |

Verdict for the rulers: eval_v2's `tol = σ + |slope|·10min` evaluated
at *overlap edges* is the right shape (it probes mid-span, not the
ink end).  Its `REFINED_PRICE_SIGMA = 1.5p` is correct at anchors,
optimistic by ~0.5–1 p on unanchored t0.  eval.py's endpoint check at
golden t1 with flat 6p is mis-shaped: it tests the label's weakest
point (ink end) — expect false misses on early-fade labels.

In ABR: median ABR on TUNE days ≈ 4.5 p → 2 p ≈ 0.45·ABR.

## (d) Trustworthy subset for tuning

`trusted = scorable(185) − TierA(44) = 141 lines`
(cf=85, ta=56).  Use it for L2 anatomy and any geometry-derived
parameter; keep the Tier-B flag handy for span-dependent stats.
For recall scoring keep all 184 — direction/span of Tier-A labels is
still informative (the clause exists; the fit is weak).

Files: `audit_lines.py` (metrics), `audit_lines.json` (per-line rows),
`audit_png/` (20 judged renders + dbg/).

## Recommended sigma (added per Lead note R10 §2, ruler=eval_v2)

Endpoint/fit residuals vs bars, per repair stratum — p50/p80/p90:

| stratum | metric | p50 | p80 | p90 | (ABR) p50/p80/p90 |
|---------|--------|-----|-----|-----|-------------------|
| text_anchor_bars (n=62) | hug4 dev | 0.25 | 0.81 | 2.03p | 0.06/0.15/0.32 |
| text_anchor_bars | end0 res | 0.00 | 0.67 | 2.35p | 0.00/0.14/0.57 |
| constrained_fit (n=122) | hug4 dev | 0.70 | 4.46 | 5.97p | 0.12/0.61/0.97 |
| constrained_fit | end0 res | 0.59 | 4.16 | 7.45p | 0.12/0.66/1.71 |
| TRUSTED pooled (n=141) | hug4 dev | 0.29 | 0.83 | 1.57p | 0.06/0.14/0.25 |
| TRUSTED pooled | end0 res | 0.00 | 1.87 | 6.20p | 0.00/0.34/1.27 |

Proposal: sigma_line = **2.0 pips** (~0.4 ABR). Covers p90 of
trusted hug residuals (1.57p) and ~p80-90 of text_anchor (2.03p).
constrained_fit's p90 sits at ~6p — a single sigma cannot be tight
and fair for both strata; 2.0p prices the trusted labels honestly
and lets the suspect tail fail as intended. (Landed as
`REFINED_LINE_SIGMA = 2.0`, Ruling 11 §11.3.)
