# REGRESSION_V0_V1 — per-object diff under eval_v2 (R10.3 item 1)

Method: every scorable golden BOX / BRACKET / LEVEL_CARRIED on 198 TUNE
panels, matched under `evalcheck/eval_v2.py` (frozen ruler) for engine
v0 (`engine_v0.py`) and v1 (current).  One engine run per panel per
version; match = greedy assignment on `eval_v2.score`.  Miss reasons
from the v1 funnel log (`cand_log`) + born-object geometry.
Script: `_regression.py`; rows: `_regression_rows.jsonl`.

## Match matrix (golden objects)

| type | golden | v0∩v1 | v0 only | v1 only | neither |
|---|---|---|---|---|---|
| BOX | 111 | 7 | **16** | 1 | 84 |
| BRACKET | 85 | 6 | **56** | 0 | 23 |
| LEVEL_CARRIED | 48 | 4 | 4 | 1 | 39 |

BRACKET is the regression: v0 62 matched -> v1 6.  v0's bracket route
is a same-side swing-pair rule on the full confirmed-pivot stream;
v1's `_brackets` runs only on the θ₂ (`structural()`) stream and
requires the completing pivot to be the last of an alternating
a-b-a triple — the template rarely fires on small formations.

## v1 miss reasons (totals)

### BRACKET — 79 misses

| reason | n |
|---|---|
| never_proposed (no candidate with matching letter+span) | **49** |
| born_wrong_edges (born bracket overlaps span but wrong letter / <0.3 coverage) | 15 |
| proposed_wrong_geom (candidate in span, wrong letter) | 8 |
| refused_rate_limited | 7 |

Generation, not selection.  9.1b golden M(627-655)+W(710-760): the
whole day produced zero BRACKET candidates near either span — the
θ₂ stream has no equal-extreme triple there.  `born_wrong_edges` is
mostly **wrong letter** on an overlapping formation (born `Mm` vs
golden `W`, born `M` vs golden `SHS`/`WW`), plus 12 golden `WW`/`MM`
letters the engine has no template for at all.

### BOX — 103 misses

| reason | n |
|---|---|
| born_wrong_edges (a box born overlapping the span, edges off golden's) | **51** |
| refused_rate_limited (right-geometry candidate, cap spent) | **40** |
| proposed_wrong_geom | 3 |
| born_geom_ok_span_fail | 2 |
| never_proposed | 2 |
| born_wrong_episode | 1 |
| refused_nms_suppressed | 1 |

The 51 are mostly *different* congestions overlapping in time (e.g.
9.2c golden [13222-13238] vs born [13311-13332]) — the golden box
itself was never proposed in its own geometry, while a neighbour
band was born.  Rate-cap refusals remain the second cause.

### LEVEL_CARRIED — 43 misses

| reason | n |
|---|---|
| refused_rate_limited | **17** |
| born_wrong_edges (born level price off golden's) | 11 |
| born_geom_ok_span_fail (right price, span disjoint) | 7 |
| proposed_wrong_geom | 6 |
| refused_expired | 1 |
| never_proposed | 1 |

## Five annotated examples per type

### BRACKET
1. `9.1b` golden `M` 627-655: **never_proposed** — no BRACKET row all
   day near the span; the M's two tops are θ₁-scale, invisible to the
   structural-only template.
2. `9.3b` golden `WW` 740-785: **never_proposed** — no `WW` template
   exists (double-W, 45min span).
3. `9.1a` golden `SHS` 367-480: **born_wrong_edges** — engine born
   `M` 240-415 overlapping it; the 5-pivot SHS predicate never fired
   (needs last-5-structural exactly s1 n1 h n2 s2).
4. `9.2c` golden `W` 1035-1070: **never_proposed** — only `M` 100-106
   proposed that day.
5. `9.51b` golden `W` 780-785 (5-min formation): **born_wrong_edges**
   — engine born `M` 420-840, different letter and 8x the span.

### BOX
1. `9.2c` golden [13222-13238] 770-965: born [13311-13332] 720-1080 —
   a different congestion one leg earlier; golden band never proposed.
2. `9.6a` golden [13167-13185] 355-630: born [13134-13182] 240-455 —
   engine took a 48-pip range where golden drew an 18-pip box; same
   region, wrong edges (excursion clusters still winning sometimes).
3. `9.7a` golden [13228-13240] 580-695: born [13260-13274] 300-660 —
   wrong region entirely; the golden buildup sits later.
4. `9.16b` golden [13141-13165] 515-865: born [13210-13218] 480-825 —
   again a neighbouring band; golden's own congestion never proposed.
5. `9.35a` golden [13101-13110] 550-623: born [13123-13134] 180-600 —
   tight 9-pip golden box vs a different 11-pip band elsewhere.

### LEVEL_CARRIED
1. `9.1a` golden 13305 (drawn ~500): right-price carry proposed at the
   box break but `rate_level_carried` slot already spent →
   refused_rate_limited.
2. `9.23c` golden carry at the box edge: same pattern — candidate
   right price, cap full (earlier box break already consumed it).
3. `9.18a` golden level at broken-box edge: born MINI_LEVEL ~7 pips
   off → born_wrong_edges.
4. `9.19a` golden carry: born right price but closed/never overlapped
   the golden span → born_geom_ok_span_fail.
5. `9.30a` golden carry: proposed at the wrong price
   (congestion_edge took the outer excursion cluster) →
   proposed_wrong_geom.

## Top causes to fix (queue order)

1. **BRACKET generation** (49 never_proposed + 15 wrong-letter):
   run the M/W pair template on the mixed-scale alive stream (θ₁
   anchors allowed; minor inner legs mark the letter), relax the
   last-3-alternating constraint to a same-side pair with an
   intervening opposite extreme.  DN_BRACKET §5 licenses the
   mixed-scale stream for the variants; golden plain M/W spans
   (median 34 min) are mostly θ₁-scale formations.
2. **BOX generation coverage** (51 born_wrong_edges are mostly
   golden-band-never-proposed): the anchor-touch route covers ~2/3;
   the rest need the congestion_scan seed to fire earlier/later —
   investigate per-panel.
3. **rate_limited** (64 across types): this is the §9.3/§9a work —
   cap pre-emption once the score separates.  Not a threshold tweak.
