# LEVEL YARDSTICK AUDIT (V1)

Scope: all golden `LEVEL_CARRIED` (48) and `MINI_LEVEL` (32) objects on TUNE v2.
Measured against bars only — no engine output read in this step. Script:
`levellab/audit_levels.py`, cache via `linelab/bars_cache.py` → `book_loader`.
Result file: `audit_levels.json` (80 objects; 78 scorable, 2 `time_only`).

## (a) Reliability per stratum

Two label-anchoring metrics, both causal (bars strictly before `t0` unless noted):

- `nearest_any_p`: distance of the label price to the nearest prior bar extreme.
  "Does the price sit on anything real?"
- `span_nearest_p`: minimum |price − any bar extreme| inside the drawn span.
  "Does the market ever come back to the level while it is drawn?"

| type | repair_method | n | anyRes p50/p90 (p) | spanNear p50/p90 (p) | prior touches p50 | span p50 (min) |
|---|---|---|---|---|---|---|
| LEVEL_C | text_anchor_bars | 22 | 1.9 / 6.8 | 0.7 / 2.0 | 6.5 | 112 |
| LEVEL_C | text_price | 20 | 1.8 / 4.1 | 0.0 / 5.4 | 7.5 | 109 |
| LEVEL_C | edge_from_bars | 4 | 5.0 / 10.3 | 0.7 / 0.8 | 2.0 | 123 |
| LEVEL_C | sibling_span | 1 | 3.4 | 0.0 | 12 | 60 |
| MINI_L | edge_from_bars | 19 | 1.1 / 2.1 | 0.7 / 5.2 | 14 | 25 |
| MINI_L | text_anchor_bars | 8 | 1.5 / 0.7 | 0.7 / 1.5 | 11 | 25 |
| MINI_L | text_price | 4 | 3.4 / 9.5 | 4.8 / 6.2 | 5.0 | 78 |

Read: bar-anchored repairs sit on real prices (median 1.1–1.9p). The tails are
the suspects below, not a tolerance problem. MINI_LEVEL is a different animal:
shorter spans (~25 min), denser prior touch counts — they are micro-support
under active price, not carried walls.

## (b) Suspect list — proposals only, yardstick stays frozen

Tier A — price is on nothing: `nearest_any_p > 4p` (11 objects):

| object | type | repair | anyRes | spanNear | note |
|---|---|---|---|---|---|
| 9.18c#0 | LEVEL_C | text_price | 19.8 | 9.2 | flag-floor price far off tape |
| 9.30b#0 | MINI_L | text_price | 12.5 | 0.0 | "prior high" 12p from any bar |
| 9.38a#1 | MINI_L | edge_from_bars | 13.8 | 8.4 | step floors mispriced |
| 9.63a#1 | LEVEL_C | edge_from_bars | 11.2 | 0.7 | dash on empty air |
| 9.60a#3 | MINI_L | edge_from_bars | 7.1 | 6.6 | — |
| 9.65a#0 | LEVEL_C | text_anchor_bars | 15.6 | 0.0 | Asia floor misprice |
| 9.23c#0 | LEVEL_C | text_price | 6.3 | 0.0 | congestion-lows ≈6p off |
| 9.26a#2 | LEVEL_C | text_anchor_bars | 8.2 | 0.7 | old-support extension off |
| 9.57b#3 | LEVEL_C | text_anchor_bars | 5.4 | 0.0 | — |
| 9.40a#0 | LEVEL_C | text_anchor_bars | 7.0 | 0.7 | Asia floor misprice |
| 9.50a#1 | LEVEL_C | edge_from_bars | 4.1 | 0.8 | borderline |

Tier B — price on a real extreme but market never returns in-span
(`span_nearest_p > 3p`; the drawn level is reference ink, not defended price):
9.1c#3 (3.2p), 9.22b#3 (5.0), 9.31b#0 (3.8), 9.33b#0 (6.4), 9.36b#3 (5.8),
9.40c#1 (19.1 — W-lows far from span), 9.51b#2 (3.7), 9.57b#2 (3.5),
9.64c#3 (4.8), 9.65a#1 (5.3). For LEVEL_CARRIED, "carried reference" is a
legitimate book role — Tier B objects are down-weighted for tuning, not wrong.
Unscorable: 9.28b#2, 9.38c#2 (`time_only`).

## (c) Supported tolerance + ruler mechanics

`eval_v2.match_detail` for levels: spans must overlap (or a point engine level
falls inside the golden span); price must be within `prec_sigmas` of the golden
price; time-only objects match on span alone. σ: `meas` 2.0p, `eye` 5.0p,
repaired (REFINED_METHODS) 1.5p; time σ = 10 min.

- Late birth is fine: any span overlap counts, so a level born a few bars
  after `t0` still matches. Fair — the level's job is the price.
- σ audit: bar-anchored residuals (median 1.1–1.9p) support the current 1.5p
  refined sigma; Tier-A suspects are 4–20p off and no σ fixes them. No ruler
  change proposed.
- τ convention: golden `t0` treated as decision time. For LEVEL_CARRIED the
  true "draw moment" is usually *before* `t0` (the level is carried across
  panels) — relevant for V2 anatomy.

## (d) Trustworthy subset

scorable 78 − TierA 11 = **67 trusted** (Tier B flagged, kept, down-weighted).
LEVEL_CARRIED trusted: 40/48. MINI_LEVEL trusted: 27/31 scorable.

## (e) Book cues defining the objects (paraphrased, no quotes >15 words)

Cue classes: `named-bar` (20) — "at the ~HH:MM low/high"; `swing/bar-ref`
(11) — support/resistance at a price; `span-only` (17, mostly MINI) — bare
"a short horizontal ~HH:MM–HH:MM", no named anchor — weakest definitional
quality; `congestion-edge` (6); `asia-extreme` (4); `bracket-extreme` (6 —
W middle/neckline, H&S head); `old-swing` (3); `breakout-level` (2);
`spike-bar` (1); `prior-day` (0); `round-number` (0); `other` (10 — raw
abbreviations like "H ~1.2702 to ~14:40", "DASH ~07:35–08:05").

Notable: **zero round-number or prior-day cues** — the author's levels are
always tape-anchored (named bars, congestion edges, session extremes). A
level origin class must come from price history, not from price arithmetic.

## Per-object table

| obj | type | price | span (min-of-day) | repair | cue | tier | anyRes | spanNear |
|---|---|---|---|---|---|---|---|---|
| 9.1b#3 | LEVEL_C | 1.3318 | 570–720 | text_price | breakout-level |  | 0.1 | 0.0 |
| 9.1c#3 | MINI_L | 1.3313 | 1070–1080 | text_anchor_bars | span-only | B | 0.1 | 3.2 |
| 9.3c#0 | LEVEL_C | 1.3215 | 853–1005 | text_price | swing/bar-ref |  | 3.8 | 0.0 |
| 9.3c#4 | LEVEL_C | 1.3217 | 1005–1045 | text_anchor_bars | swing/bar-ref |  | 0.2 | 0.0 |
| 9.4a#2 | MINI_L | 1.3191 | 485–545 | text_anchor_bars | bracket-extreme |  | 0.2 | 0.0 |
| 9.4a#4 | MINI_L | 1.3198 | 575–600 | edge_from_bars | span-only |  | 0.1 | 0.7 |
| 9.5c#1 | LEVEL_C | 1.3137 | 1020–1080 | sibling_span | congestion-edge |  | 0.1 | 0.0 |
| 9.6c#0 | LEVEL_C | 1.3223 | 833–930 | text_price | congestion-edge |  | 0.1 | 1.8 |
| 9.11b#4 | MINI_L | 1.3050 | 775–795 | edge_from_bars | span-only |  | 0.3 | 0.7 |
| 9.12a#2 | MINI_L | 1.3077 | 620–640 | text_anchor_bars | named-bar |  | 0.2 | 0.8 |
| 9.14a#1 | MINI_L | 1.3242 | 495–515 | text_anchor_bars | named-bar |  | 0.2 | 0.7 |
| 9.14c#0 | MINI_L | 1.3183 | 810–840 | text_anchor_bars | swing/bar-ref |  | 0.5 | 0.0 |
| 9.15b#2 | MINI_L | 1.3228 | 890–920 | text_anchor_bars | swing/bar-ref |  | 0.2 | 0.0 |
| 9.17b#0 | MINI_L | 1.3235 | 555–580 | edge_from_bars | span-only |  | 0.9 | 0.7 |
| 9.17b#1 | LEVEL_C | 1.3265 | 605–780 | text_anchor_bars | named-bar |  | 2.0 | 0.0 |
| 9.17b#3 | LEVEL_C | 1.3263 | 720–840 | text_price | named-bar |  | 0.1 | 0.0 |
| 9.18c#0 | LEVEL_C | 1.3338 | 880–965 | text_price | swing/bar-ref | A | 19.8 | 9.2 |
| 9.21b#0 | LEVEL_C | 1.3292 | 725–855 | text_price | swing/bar-ref |  | 0.6 | 1.8 |
| 9.21c#3 | MINI_L | 1.3282 | 1015–1030 | edge_from_bars | span-only |  | 0.0 | 0.7 |
| 9.22a#1 | MINI_L | 1.3349 | 580–595 | edge_from_bars | span-only |  | 0.1 | 0.7 |
| 9.22b#1 | MINI_L | 1.3353 | 690–715 | edge_from_bars | span-only |  | 0.0 | 0.7 |
| 9.22b#3 | LEVEL_C | 1.3337 | 720–765 | text_price | span-only | B | 0.2 | 5.0 |
| 9.22c#2 | MINI_L | 1.3336 | 1035–1085 | edge_from_bars | span-only |  | 0.2 | 0.7 |
| 9.23c#0 | LEVEL_C | 1.3318 | 841–1055 | text_price | congestion-edge | A | 6.3 | 0.0 |
| 9.24c#2 | MINI_L | 1.3325 | 880–965 | text_anchor_bars | bracket-extreme |  | 1.3 | 0.7 |
| 9.25a#0 | LEVEL_C | 1.3187 | 290–640 | text_price | congestion-edge |  | 1.2 | 0.0 |
| 9.25c#1 | LEVEL_C | 1.3136 | 952–983 | text_price | bracket-extreme |  | 0.2 | 0.0 |
| 9.26a#2 | LEVEL_C | 1.3129 | 545–630 | text_anchor_bars | old-swing | A | 8.2 | 0.7 |
| 9.28b#2 | LEVEL_C | — | — | time_only | span-only |  | — | — |
| 9.30b#0 | MINI_L | 1.3121 | 505–548 | text_price | old-swing | A | 12.5 | 0.0 |
| 9.31b#0 | LEVEL_C | 1.3139 | 660–745 | text_price | spike-bar | B | 0.0 | 3.8 |
| 9.32b#0 | LEVEL_C | 1.3167 | 561–710 | text_price | swing/bar-ref |  | 0.0 | 0.0 |
| 9.33b#0 | MINI_L | 1.3036 | 425–710 | text_price | named-bar | B | 2.6 | 6.4 |
| 9.33c#0 | LEVEL_C | 1.3029 | 920–985 | text_price | breakout-level |  | 0.3 | 0.0 |
| 9.34a#2 | MINI_L | 1.3092 | 535–545 | edge_from_bars | span-only |  | 0.1 | 0.7 |
| 9.34b#2 | MINI_L | 1.3144 | 660–700 | edge_from_bars | other |  | 0.0 | 0.7 |
| 9.35b#1 | MINI_L | 1.3081 | 855–875 | edge_from_bars | span-only |  | 0.2 | 2.6 |
| 9.36b#3 | MINI_L | 1.3128 | 745–810 | text_price | swing/bar-ref | B | 0.3 | 5.8 |
| 9.37c#2 | LEVEL_C | 1.3176 | 860–940 | text_anchor_bars | congestion-edge |  | 0.6 | 0.7 |
| 9.38a#1 | MINI_L | 1.3165 | 495–530 | edge_from_bars | swing/bar-ref | A | 13.8 | 8.4 |
| 9.38c#2 | MINI_L | — | — | time_only | span-only |  | — | — |
| 9.39b#2 | LEVEL_C | 1.3150 | 645–770 | text_anchor_bars | swing/bar-ref |  | 0.0 | 0.7 |
| 9.39b#4 | MINI_L | 1.3151 | 740–770 | edge_from_bars | span-only |  | 0.1 | 0.7 |
| 9.40a#0 | LEVEL_C | 1.3185 | 255–535 | text_anchor_bars | asia-extreme | A | 7.0 | 0.7 |
| 9.40b#0 | LEVEL_C | 1.3197 | 540–830 | text_price | asia-extreme |  | 0.0 | 0.0 |
| 9.40c#1 | LEVEL_C | 1.3194 | 911–963 | text_price | bracket-extreme | B | 1.4 | 19.1 |
| 9.42c#1 | MINI_L | 1.3240 | 910–960 | edge_from_bars | other |  | 0.0 | 0.7 |
| 9.48c#2 | LEVEL_C | 1.3027 | 736–820 | text_price | bracket-extreme |  | 0.1 | 0.0 |
| 9.49a#0 | LEVEL_C | 1.3027 | 591–630 | text_price | swing/bar-ref |  | 0.1 | 0.0 |
| 9.50a#1 | LEVEL_C | 1.2997 | 545–600 | edge_from_bars | bracket-extreme | A | 4.1 | 0.8 |
| 9.51a#1 | LEVEL_C | 1.2944 | 480–605 | text_anchor_bars | named-bar |  | 0.0 | 0.7 |
| 9.51b#2 | MINI_L | 1.2950 | 705–795 | text_price | congestion-edge | B | 0.0 | 3.7 |
| 9.52a#1 | LEVEL_C | 1.2932 | 340–600 | text_anchor_bars | named-bar |  | 0.1 | 2.1 |
| 9.52b#1 | LEVEL_C | 1.2928 | 650–840 | edge_from_bars | span-only |  | 0.1 | 0.7 |
| 9.54b#1 | MINI_L | 1.2856 | 815–825 | text_anchor_bars | named-bar |  | 0.0 | 0.7 |
| 9.56b#2 | LEVEL_C | 1.2731 | 615–670 | text_anchor_bars | named-bar |  | 0.1 | 0.7 |
| 9.57b#1 | LEVEL_C | 1.2684 | 675–840 | text_anchor_bars | named-bar |  | 0.2 | 0.0 |
| 9.57b#2 | LEVEL_C | 1.2680 | 625–645 | text_anchor_bars | named-bar | B | 0.0 | 3.5 |
| 9.57b#3 | LEVEL_C | 1.2700 | 625–705 | text_anchor_bars | old-swing | A | 5.4 | 0.0 |
| 9.57b#4 | LEVEL_C | 1.2690 | 710–760 | text_anchor_bars | named-bar |  | 0.0 | 0.7 |
| 9.57c#0 | LEVEL_C | 1.2702 | 880–935 | text_price | other |  | 0.1 | 0.1 |
| 9.58a#0 | LEVEL_C | 1.2781 | 290–650 | text_anchor_bars | asia-extreme |  | 2.2 | 0.0 |
| 9.59a#2 | LEVEL_C | 1.2782 | 535–630 | text_anchor_bars | named-bar |  | 0.1 | 0.7 |
| 9.59c#0 | LEVEL_C | 1.2775 | 840–1055 | text_anchor_bars | named-bar |  | 0.3 | 0.0 |
| 9.60a#0 | LEVEL_C | 1.2681 | 385–590 | text_anchor_bars | named-bar |  | 0.1 | 0.7 |
| 9.60a#3 | MINI_L | 1.2651 | 580–605 | edge_from_bars | other | A | 7.1 | 6.6 |
| 9.60b#0 | LEVEL_C | 1.2678 | 561–905 | text_price | named-bar |  | 0.2 | 0.0 |
| 9.60b#5 | LEVEL_C | 1.2650 | 805–885 | text_anchor_bars | named-bar |  | 0.5 | 0.7 |
| 9.61c#0 | LEVEL_C | 1.2577 | 735–1095 | text_price | other |  | 0.0 | 0.0 |
| 9.61c#4 | MINI_L | 1.2575 | 1035–1070 | edge_from_bars | other |  | 0.1 | 0.7 |
| 9.62b#1 | MINI_L | 1.2594 | 735–795 | edge_from_bars | other |  | 0.2 | 0.7 |
| 9.63a#1 | LEVEL_C | 1.2609 | 455–485 | edge_from_bars | span-only | A | 11.2 | 0.7 |
| 9.64a#0 | LEVEL_C | 1.2527 | 395–495 | text_anchor_bars | named-bar |  | 0.1 | 0.0 |
| 9.64c#3 | MINI_L | 1.2528 | 1010–1025 | edge_from_bars | other | B | 0.1 | 4.8 |
| 9.65a#0 | LEVEL_C | 1.2442 | 280–625 | text_anchor_bars | asia-extreme | A | 15.6 | 0.0 |
| 9.65a#1 | LEVEL_C | 1.2481 | 540–590 | text_anchor_bars | named-bar | B | 0.2 | 5.3 |
| 9.66a#1 | MINI_L | 1.2387 | 520–575 | edge_from_bars | other |  | 0.2 | 0.7 |
| 9.66a#2 | MINI_L | 1.2406 | 575–595 | edge_from_bars | other |  | 0.5 | 0.7 |
| 9.66c#0 | LEVEL_C | 1.2395 | 755–975 | text_anchor_bars | named-bar |  | 0.0 | 0.0 |
| 9.66c#1 | LEVEL_C | 1.2379 | 720–910 | edge_from_bars | span-only |  | 0.3 | 0.7 |
