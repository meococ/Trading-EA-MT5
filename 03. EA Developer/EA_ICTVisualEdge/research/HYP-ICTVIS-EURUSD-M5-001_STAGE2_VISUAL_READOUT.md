# Stage-2 Visual Readout — HYP-ICTVIS-EURUSD-M5-001

DESIGN window 2015-2018 ONLY. Method = `AI_EXPLORATORY` idea-generation: the eye
reads asof (decision-time) charts and proposes candidate discriminating features.
The eye produces HYPOTHESES only; every feature is quantified and its separation
measured mechanically on DESIGN, then frozen and tested on sealed TRAIN/VAL/holdout.

Sample: 40 balanced asof charts (20 TP winners, 20 SL/BOTH losers) spread across
2015-2018, M5, from the generous sweep universe (base win-rate 34.5% at 2R).
Charts: `evidence/stage1/charts_design/`.

## Observations (winners vs losers)

- **Winner shorts** (e.g. 2015-02-11 16:20, 2016-07-01 19:35): entry at a level
  that had been **touched/tested multiple times** (well-defined S/R), reached after
  **sideways / rounded exhaustion**, entry near a **range extreme**, small SL.
- **Loser shorts** (e.g. 2015-02-10 13:40, 2016-07-11 10:10): entry taken **into a
  rising leg** — the bars immediately before entry are large-bodied moves AGAINST
  the trade (shorting into momentum); entry often sits **mid-range**, not at a
  clean tested extreme.

## Candidate feature hypotheses (declared BEFORE quantification)

| id | feature | rationale | decision-time safe |
|----|---------|-----------|--------------------|
| F1 | approach_momentum (adverse) | losers fade a fresh impulse; feature = trade-direction return over last k bars / ATR (negative = entering against momentum) | uses bars <= i |
| F2 | approach_velocity_abs | steepness of the leg into entry / ATR | bars <= i |
| F3 | level_touch_count | prior bars within X pips of swept extreme (level quality) | bars <= i |
| F4 | sweep_wick_ratio | rejection wick on sweep bar / bar range | bar i only |
| F5 | range_position | entry location in recent N-bar range (shorts want high) | bars <= i |
| F6 | compression | short-window ATR / long-window ATR (consolidation before) | bars <= i |

## De-dup mapping check (auto-fail predicate)

Every surviving feature is mapped to the killed ICT primitive set
`{sweep, displacement/MSS/BOS, FVG/OB retest, killzone, HTF-bias}`. Note F1/F2
sit in the displacement GREY ZONE: "avoid entering against recent displacement"
is the *inverse context* of the displacement primitive, not the displacement
edge itself. This mapping is adjudicated explicitly in the Stage-3 freeze:
- If the surviving edge is essentially "trade the displacement" -> auto-FAIL.
- If it is a level-quality / mean-reversion-context feature (F3/F5/F6) or a
  momentum-CONTEXT filter that is provably not the displacement entry trigger,
  it may pass, logged feature-by-feature.

Outcome labels were NOT shown to the eye during feature proposal (only asof
images + win/loss tag for sampling balance). Quantified separation follows in
`stage2_features.py` DESIGN report.
