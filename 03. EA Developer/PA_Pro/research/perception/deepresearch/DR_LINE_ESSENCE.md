# DR-LINE — The Essence of Drawing Lines Like a Professional

Lane: DR-LINE (Lead mandate, 23/09; Ruling 69). Research-only. All
measurements read-only via `research/perception/tools/heavy_run.py`;
ruler = `evalcheck/eval_v2.py` imported, never copied.

The Owner's question: *what IS drawing a line like a pro, in essence —
and can we quantify it in a way that stays true to the essence and even
beats human subjectivity?*

**Short answer.** A professional's line is not a fit to price and not
a prediction. It is the **operational boundary of the current price
structure**: a defended edge, drawn once the market has proven it twice,
kept while it keeps explaining price, and retired when it stops. Its
value is that it is *few, causal, and stable* — the chart shows the
two or three references that currently matter, and nothing else. The
engine's biggest gap is not scoring quality but **economic-legality**:
hard birth gates reject most edges the author actually draws (only 22%
of golden lines are even reachable), while noise-fragile anchors make
the survivors unstable under sub-pip feed jitter. Where the machine can
beat the human is exactly where the human is inconsistent: **stability**
(same information → same drawing) and **discipline** (every drawn edge
carries its evidence count).

---

## E1 — What the sources say

### What professionals say (Volman, via `golden/book_loader.py` notes)

From the golden `lesson`/`raw_drawn` text and the lab notes
(`linelab/LINE_ANATOMY.md`, `levellab/LEVEL_ANATOMY.md`):

- **A line is the edge of a pattern.** A break matters only because the
  edge exists. One straight line or one box usually suffices for the
  immediate price action — the chart is deliberately sparse.
- **Anchors are wave extremes — wicks, not closes.** Measured golden
  lines sit within ~1–2 pips of the touched wicks; squeeze bars may sit
  1–4 pips off. Touch = wick proximity; break = close through.
- **More bounces strengthen the edge** — and imply more buildup is
  needed for a convincing break.
- **A penetration alone is not a signal.** Teases and false-break traps
  are expected; do not redraw on the first false break.
- **Revised edges are drawn separately, not silently mutated.**
  Re-anchor only after later highs/lows confirm the new edge; skip
  isolated long-tail false extremes when fitting.
- **Edges behave like zones even when rendered as hairlines.**
- **Lines extend right beyond the break** (~3–17 bars in the measured
  drawings), then the residual is carried as a horizontal level — the
  broken barrier flips role (support becomes resistance).
- **Levels are memory.** Prior turns, pauses, congestions, session
  extremes; the nearest prior level is often the stronger magnet; the
  birth price is retained while the span extends; a level's usefulness
  runs a lifecycle: touches → hold/magnet → break → revisit/role
  reversal → next level.

### Other professionals

- **Al Brooks**: trendlines through meaningful swing points; the third
  contact confirms; the *reaction away* from a point matters more than
  the touch; best-fit lines describe channels but are less causal and
  less stable than explicit swing-edge construction.
- **Wyckoff**: the "line of least resistance", creek/ice, back-up —
  S/R are zones built by prior rallies and reactions; a decisive break
  followed by a retest confirms role reversal.
- **Auction-market theory (Steidlmayer, Dalton)**: markets alternate
  between imbalance and balance; boundaries of value areas are
  negotiated regions, not exact ticks.
- **Edwards & Magee**: trendlines through reaction extremes;
  penetration rules judged on closes with a margin; the same
  "poke vs decisive traverse" grammar Volman uses on M5.

### What academic/empirical work supports

- **Osler (2000), FRBNY**: published S/R levels predict intraday
  interruptions of trends; predictive power varies by provider; levels
  retain effect across days — supports *memory/carry-over*.
- **Osler (2003)**: stop-loss and take-profit orders cluster at
  technical and round-number levels; crossing them produces unusually
  rapid movement — a micro-mechanism for "the edge matters because
  orders sit there".
- **Kavajecz & Odders-White (2004)**: support/resistance levels
  coincide with peaks in limit-order-book depth — technical levels mark
  where liquidity already exists.
- **Garzarelli et al. (2014)**: prices rebound more often than they
  cross selected S/R values; **the probability of another bounce rises
  with the number of prior bounces** — the memory dose-response our
  DESIGN data independently reproduce (E3c).
- **Lo, Mamaysky & Wang (2000)**: subjective chart patterns can be
  defined algorithmically through smoothing + geometric conditions;
  statistical pattern detection ≠ trading profit — the ruler measures
  the former and this lane never claims the latter.
- **DR_BOX_SELECTION.md (ours)**: youngest-born box wins, hindsight
  rejected, ~30% ceiling for matching one person's idiosyncratic
  choices — the fidelity ceiling framing applies to lines too.

### What remains subjective / non-identifiable

- Which of several eligible pivot pairs is *the* edge (the author's
  choice is real but idiosyncratic — ceiling ~30% for exact matching
  of one person's selection; measured best rule ≈0.19–0.30).
- Wick vs body for anchors (book implies wick for touch, close for
  break — a convention, not a law).
- Exactly how many closes constitute a "decisive" traverse.
- When a confusing edge should be deleted rather than revised.
- Whether a drawn price is ever *the* cause of a reaction — the
  zone-vs-empty contrast stayed non-identifiable in R01/R02 and again
  here (E3c); all honest claims are about **marked-vs-marked** and
  **event-vs-hover** contrasts.

---

## E2 — First-principles definitions

### The essence, stated

**P1 — A drawn line is a defended edge, not a fit.** It is the
frontier price has respected, not the line that minimizes distance to
price. Regression/best-fit semantics are *wrong semantics*: they place
the line inside the mass of price rather than at its boundary.

**P2 — An edge is asymmetric.** It has a defended side (touches are
valuable evidence) and a violated side (excursions are damage). A top
line that rises steeply is not an edge of resistance — it is a chord
through congestion.

**P3 — A level is a remembered price, rendered as a zone.** The market
returns to prices where it previously turned (resting orders,
participants' memory — Osler, KOW). The hairline on the chart is a
compact display of a small zone, and the zone's effective edge may
shift within a band as new defences arrive — the Owner's own
formulation ("a small zone that can shift, not an exact thin line") is
the correct one.

**P4 — Evidence threshold.** Two defended extrema create a drawable
edge; a third contact confirms it (Brooks/Volman). Touches count only
on the defended side; pokes through that re-enter are teases, not
disproof.

**P5 — Lifecycle, not static object.** tentative → confirmed →
touched/poked → decisively broken (consecutive closes through) →
carried as horizontal residue (role reversal) → retired (stale). A
line that no longer explains price is deleted.

**P6 — Economy.** A professional chart shows the *operative* edges —
usually one per side, plus the nearest horizontal references. Every
drawn object must justify its ink as *the* boundary of current
structure. Selection is not "best quality" but "which edge is
operative now" — measured: the author's choice is better predicted by
structural freshness than by touch-count quality (E3a).

**P7 — Consistency (the machine's edge).** The same information must
produce the same drawing — across feed jitter, warm-up shifts, and
timeframe resampling. This is where a machine can exceed human
subjectivity, and where the current engine is weakest (E3b).

**P8 — Causality.** Only bars ≤ decision time. Any re-anchor is a
*new drawing event* (new ink or explicit revision event), never a
silent geometry mutation — golden convention: revised edges are drawn
separately.

**P9 — Revision discipline.** Do not redraw on the first false break;
revise only when later structure has produced a demonstrably better
defended edge; keep the old ink as history, not as an overwritten
object.

**P10 — Zones, not ticks.** All matching, touching, and breaking
decisions operate on zones of width ≈ max(1–1.5 pips, 0.25·ABR);
geometry stored exact is a display convenience, semantics are zonal.

### Measurable definitions (causal, ABR-normalized, cheap)

| Concept | Definition | Principle | Arbitrary? |
|---|---|---|---|
| anchor | bar extreme at a confirmed turn (DC pivot), named-bar local extremum, or running session extreme | P1/P3 | which pool members — arbitrary; measured: author favors freshest structure |
| touch | defended-side bar extreme within `tol = max(1.0–1.5p, 0.25·ABR)` of edge, deduped into events | P2/P10 | tol floor — arbitrary, standardize |
| bounce | touch followed by ≥0.5·ABR excursion on defended side within H bars before a traverse | P4 | H — arbitrary, standardize |
| poke/tease | extreme crosses edge beyond tol but close re-enters | P5 | none — principled |
| break/traverse | ≥ `pierce_dead_bars` (=2) consecutive closes through | P5 | count — arbitrary, standardize |
| overshoot | max violation of defended side by in-span pivots (and closes) | P2 | veto vs penalty — see E4 |
| enough evidence | ≥2 anchors + ≥1 mid defended touch event (3 contacts) | P4 | none — matches book |
| invalidate | traverse → convert to carried level; re-enter within grace → tease | P5 | grace length — arbitrary |
| redraw | only when a newer defended edge supersedes the operative one; draw as new ink | P8/P9 | supersession margin — arbitrary |
| retire | no touch for ~5h (≈60 M5 bars) | P3/P6 | window — arbitrary, matches level-premium decay (R11/DR-MARKET) |
| level birth | price approaches a defended origin that is the nearest same-side such price | P3/P6 | approach distance — arbitrary |

### The arbitrary-choice register

Choices the principle does NOT fix — make them once, consistently,
and report sensitivity: touch tolerance floor, break-close count,
grace/retire windows, the exact supersession margin, approach
distance. Choices the principle DOES fix: anchors are defended
extrema (wicks); touches are defended-side zonal events; breaks are
close-through events; revisions are new ink; the number of drawn
edges is small.

---

## E3 — Measurements

### E3a — Fidelity on TUNE (ruler: `eval_v2.py`; cumulative-ink)

Funnel for golden objects (scripts: `DR_LINE_fidelity.py`,
`DR_LINE_reach.py`, `DR_LINE_relax.py`, `DR_LINE_sel.py`,
`DR_LINE_null.py`):

| type | n | legal reach | proposed | born (cum-ink) |
|---|---|---|---|---|
| PATTERN_LINE | 184 | 0.21 | 0.21 | 0.11 |
| CONTEXT_LINE | 9 | 0.44 | 0.33 | 0.33 |
| LEVEL_CARRIED | 47 | 0.81 (origin-in-tol) | — | 0.19 |
| MINI_LEVEL | 30 | 0.90 | — | 0.07 |

Reach decomposition over 193 golden lines (relaxed-legality ladder):

```
v0_base    0.22   med_cands  18      vA_noveto  0.56  203
vB_nev2    0.30   med_cands  27      vC_noslope 0.26   52
vD_A_B     0.62   med_cands 226      vE_A_B_C   0.68  442
vF_wide    0.68   med_cands 760
```

- The **defended-edge veto** (no in-span pivot beyond `2·tol` on the
  violated side) is the single binding constraint: removing it triples
  reach to 0.56. The author's drawn lines routinely have interior
  pivots poking past the hairline — because the essence is the zone,
  not the exact chord (P10), and because anchors on the newest leg can
  postdate interior violations (P6).
- Slope-direction rule and `min_touch_events≥3` each cost ~4–8 pts of
  reach; span caps are non-binding.
- ~32% of golden lines remain unreachable even with all gates relaxed —
  the anchor pool itself lacks the author's anchor bars (residual =
  anchor-pool gap, incl. the ~9% named-leg-extremes class noted in
  LINE-LAB L2).
- Relaxation causes candidate explosion (med 203–760/panel): legality
  cannot be the economy mechanism. **P6 must live in selection.**

Selection over the relaxed legal space, joint top-2 ranking:

```
young_a@2  0.18-0.30   ya_ev@2 0.19   ya_prox@2 0.19
n_ev@2     0.05        lab@2   0.05   over/prox 0.04-0.12
```

- **Freshest-anchor selection beats every quality ranker.** The
  author's line is the boundary of the newest structure, not the
  historically best-scoring chord — direct P6 evidence and the same
  youngest-wins finding as DR_BOX_SELECTION.
- Nulls (line reach): cross-panel 0.026 (the matches are real), price
  shifts ±20p → 0.25–0.32 (the ruler's tolerance absorbs ±20p of
  price error — a ruler resolution limit, not a reach artifact),
  time shifts −60m 0.50 / +120m 0.03 (ruler resolves ~60min of
  span displacement).
- **Levels: presence is non-selective.** 0.85 of golden levels have a
  defended origin within tol — but so do 74–83% of ±12p-shifted
  placebo prices. The origin registry densely covers the day's range;
  the level question is entirely *which origin + when* (P6), not
  whether a defended price exists. Best read-only rule
  (`ndef_dist@2`, defended count + proximity): 0.32 LC / 0.23 MINI vs
  engine births 0.19 / 0.07.

### E3b — Consistency (`DR_LINE_consistency.py`; 198 panels × 10 variants)

- **Determinism: 0/198 panels differ** on identical re-run.
- Keep-rate of base-matched golden objects under perturbation:

| variant | PATTERN_LINE | LEVEL_CARRIED | CONTEXT_LINE |
|---|---|---|---|
| shift 1–5 bars | 0.81–0.86 | 0.38–0.88 | 0.67–1.00 |
| shift 10 | 0.71 | 0.62 | 0.67 |
| jitter ±0.3 pip | **0.48–0.57** | 0.25–0.62 | 0.67–1.00 |
| M15 resample | **0.19** | 0.38 | 0.67 |

- Flicker: churn med **2.07 events/h** (≈5 births + 5 closes +
  **3 silent re-anchors** per ~2.6 h panel); m15 churn 0.83/h.
- Reading: the engine is deterministic and robust to warm-up shifts,
  but **noise-fragile** — sub-pip wick noise flips pivot/anchor
  eligibility (a step function of exact h/l prices), halving line
  recall; M15 kills 4/5 of line matches (fine anchors invisible at
  coarse TF — partly inherent, partly fixable via zone-snapped
  anchors, EX3). Three silent geometry mutations per panel violate
  P8/P9 (revised edges should be separate ink).

### E3c — Descriptive validity on DESIGN 2016–2021
(`DR_LINE_validity.py`; EURUSD M5, every-21st-day ≈104 days;
design pre-registered in DR_LINE_LOG before measuring; value-blind —
path excursions only, no outcomes/PnL/setups)

Arrival = close enters `tol` zone of a replayed defended-origin after
≥12 closes beyond 1.75·ABR on the defended side.

| arm | n | P(first ±0.5·ABR exit = defended) | bounce ABR | pierce ABR |
|---|---|---|---|---|
| arrival at origin, n_def≥1 (all) | 303 | 0.86 | 2.4 | 2.1 |
| — of which n_def≥2 (TREAT) | 115 | **0.88** | 2.87 | 1.96 |
| hover-crossing, same origins (INCIDENTAL) | 660 | 0.72 | 1.42 | 0.81 |
| placebo price ±8p, same arrivals | 606 | 0.50* | 2.95 | 2.90 |
| CTRL0 (marked, never defended) | 0 | — | — | — |

- **Identifiable contrast (within-origin):** a genuine return to a
  defended price exits on the defended side 88% vs 72% for a hover
  crossing of the *same* price — the "return to the level" event
  carries signal beyond the level's mere presence.
- **Dose-response (Garzarelli-type memory):** median bounce/pierce
  asymmetry grows with n_def: 2.24/2.17 → 2.57/2.12 → 3.10/1.85 for
  n_def = 1 / 2–3 / 4+.
- **CTRL0 empty by construction** — an origin's birth touch counts as
  its first defence, so "marked but undefended" does not exist in this
  design; the defended-vs-fresh contrast is **not identifiable** here
  and the n_def gradient is reported as descriptive (n_def also proxies
  for congested location — stated confound).
- *Placebo ±8p is positional by construction (0.99/0.01 split by
  direction): it bounds what "holding" means geometrically but is not a
  fair null — reported for honesty, not used as evidence.*
- **R01 confound confirmed:** fast approaches defend less (0.80) than
  slow (0.92) and pierce deeper (2.46 vs 1.37 ABR) — any future
  validity test must match approach speed.

Verdict: **descriptive support** for P3/P4 — price reacts at defended
prices, more so on genuine returns and with more prior defences. The
strong "this price vs no price" claim remains non-identifiable (R01/R02
lesson holds).

---

## E4 — Engine vs the essence

### `lines.py` — compliance map

| Principle | Status | Evidence |
|---|---|---|
| P1 edge semantics | **follows** | candidates are hull edges through pivots; `_scan` pairs anchors only from the defended-side pool — `lines.py:136-160` |
| P2 asymmetry | **follows, too hard** | slope rule `:171-176`; defended-veto kills chords with any in-span pivot `>2·tol` past the edge `:181-203` — the veto that costs 34pts of golden reach |
| P4 evidence | **follows** | `min_touch_events=3` = 2 anchors + defended mid touch `:211-225` |
| P5 lifecycle | **follows** | poke/tease vs traverse grammar `:415-460`; `pierce_dead_bars=2`; `broken_line_edge` carry spawn `:449`; bounded dashed extension `extend 3–17` ≈ book's measured range |
| P6 economy | **violates** | legality over-filters *before* selection (reach 0.22) while selection ranks generic quality not operative-edge-ness; youngest-edge evidence unused — `_eval` proposes single best-by-`nt` chord `:234-236`, salience orders by touches/span/prom/prox `salience.py:276-283` |
| P7 consistency | **partially violates** | deterministic, but anchors are step functions of exact wick prices — jitter halves recall (E3b); `_is_loc_ext` `:100-124`, DC pivot confirmation in `swings.py` |
| P8 causality | **follows** | eval only on confirmed pivots/anchors `t_conf<=i` `:260`, trigger-on-confirm `:38`, terminal anchors are still bar-causal `:362-380` |
| P9 revision | **violates** | re-anchor mutates `p0/slope` in place `:297-311` — golden draws revised edges separately; median 3 silent mutations/panel |
| P10 zones | **follows** | all touch/break tests use `tol = max(1.0p, 0.25·ABR)` `:243` |

### `levels.py` — compliance map

| Principle | Status | Evidence |
|---|---|---|
| P3 memory | **follows** | birth price frozen, span extends, depth consumed per touch `levels.py:184-220`; defended-origin registry merges in-band keeping the defended edge `:235-259` |
| P10 zone | **follows** | asymmetric `z_near/z_far` render `:412-414`; reprice-in-band `:385-397` — implements "zone that can shift" |
| P5 lifecycle | **follows** | traverse death (2 closes) `:454-460`; stale death `:465`; departure death `:449-453`; revive within `def_revive_bars` `:400-411` |
| P6 economy | **partially** | live budget + eviction hysteresis `:297-334` is a good economy mechanism — but the birth trigger `:336-346` is proximity-only: any origin within `1.75·ABR` with `n_def≥2` fires, no "nearest defended price" check despite the registry's density (E3a nulls) |
| P8 causality | **follows** | origins from confirmed pivots + running session extremes only `:136-176` |

### `salience.py` — compliance map

- **follows P6 mechanism**: score → NMS → hysteresis → budget
  (`salience.py:50`, `round` `:530`); `fam_budget=1` matches the
  author's per-family live count `:750-774`; dead/broke objects
  reclass to context ink `:733-745` (the broken-line carry is residual,
  not signal — correct).
- **violates P6 semantics**: the score terms (touches, span, prom,
  recency, prox `:276-283`) contain no "operative boundary of the
  newest structure" term — measured: freshness rankers beat them
  3–5× on golden line@2.
- `level_touch_rec` (`:253-275`) already scores levels by causal
  touch-count × recency — closer to the essence than the generic path.
- grave-band suppression `:133-172` can block legitimate re-draws;
  engine-side revive `lines.py:316-336` exists precisely to bypass it.

---

## E4 — Flagged experiments (≤2 variants each; all parameters stated;
all causal; ranked by expected gain)

**EX1 — Soften the defended-veto (biggest measured headroom: reach
0.22 → 0.56–0.68).**
- A `line.over_veto_mode = "soft"`: no hard reject; overshoot enters
  the score via existing `overshoot_w` (lab scorer already implements
  `nt − w·over_all/tol`, `salience.py:333`). Params: `overshoot_w=0.5`,
  `over` computed on pivots AND closes (lab's `worst_c`, `:310-322`).
- B `line.over_veto_mode = "close_only"`: veto only on in-span *close*
  violations `> 2·tol`; wick pokes allowed (a poke is a tease — P5 —
  not a falsified edge). Same `tol`, no new params.
- Expected: reach ~0.5+. Risk: candidate explosion — must ship with
  EX2's selection or clutter floods the budget.

**EX2 — Operative-edge selection for lines (measured: 0.19–0.30 vs
0.05–0.12 for quality rankers).**
- A `line.rank = "edge_age"`: candidate feature `edge_age_min` =
  `(i − second_anchor.t_ext)·5`; salience sorts line candidates by
  smallest `edge_age` first (boundary of the newest leg), ties by
  `nt`.
- B `line.rank = "young_a"`: prefer the chord whose *first* anchor is
  freshest (the newest structure's boundary), measured best single
  rule. Params: none beyond sort key; keep `min_touch_events=3` as the
  evidence floor.

**EX3 — Zone-stable anchors (targets the jitter gap 0.48–0.57).**
- A `line.anchor_snap = 0.5·tol`: snap candidate anchor prices to a
  0.5·tol grid before pairing — sub-tol wick noise cannot change the
  chord. Cheap, purely geometric.
- B `swing.prom_snap = true`: compute pivot prominence on snapped
  prices — fixes the fragility upstream (anchor *existence*, not just
  pairing). Slightly deeper change; bigger stability gain expected.

**EX4 — Revision as ink, not mutation (P8/P9; kills 3 silent
re-anchors/panel).**
- A `line.reanchor_ink = true`: on a qualifying re-anchor, close the
  old line (solid span ends at revision bar, keep dashed per existing
  extension grammar) and birth the new chord as a sibling object —
  matches golden "revised edges drawn separately". Ink cost +1
  residual; no budget change (old line goes context-ink).
- B `line.reanchor_log = "revise"`: keep in-place mutation but emit an
  explicit `revise` event carrying old+new geometry — minimum-cost
  honesty for the log/ruler.

**EX5 — Level birth = nearest defended origin (levels; the registry is
dense — presence non-selective).**
- A `level.def_nearest = true`: `_trigger` fires only if the origin is
  the nearest same-side origin to `c` among all `n_def≥2` origins —
  the book's "nearest prior level is the stronger magnet" (P3/P6).
- B additionally `level.def_ret24_req = true`: require a defence within
  `def_ret24_bars` — memory must be fresh to be operative.
- Expected: fewer, better-timed births; `ndef_dist@2` evidence (0.32
  vs 0.19) suggests modest recall gain and lower clutter.

*Not proposed (ruled out by measurement): widening tolerances (vF adds
no reach beyond vE at 760 candidates); flat-slope floor variants
(non-binding); outcome-based filters (walled).*

## Proposed extra metrics for the Owner (proposals only — M1/M2, the
ruler, thresholds, fixtures and the spec are Owner-owned)

- **M3 stability**: keep-rate of base-matched objects under ±0.3-pip
  jitter and M15 resample (today: lines 0.48–0.57 / 0.19 — headroom).
- **M4 churn**: lifecycle events/hour + silent re-anchor count
  (today 2.07/h, 3/panel).
- **M5 snapshot fidelity**: `evalcheck/snapshot.py` already implements
  recall-at-decision-time vs cumulative-ink; report beside M1/M2 —
  the essence asks "was the right reference drawn when it mattered",
  which cum-ink over-credits.

## Limitations

- Fidelity numbers are cumulative-ink; snapshot numbers would be lower.
- Golden ceiling ~30% for one person's selection (DR_BOX_SELECTION) —
  recall scores must be read against idiosyncrasy, not as absolute
  quality.
- Level "reach" is a density statistic (registry covers the range);
  the real question is selection — measured via rules, not funnel.
- E3c is descriptive for the defended-vs-fresh contrast (CTRL0 empty);
  the placebo arm is positional by construction; n_def confounds with
  congestion.
- M15 line instability is partly intrinsic (fine anchors genuinely
  invisible at coarse TF); the fixable part is anchor-zone snapping.

---

## E5 — Tóm tắt cho anh (10 dòng, nói đơn giản)

1. Line của dân chuyên không phải đường fit cho đẹp — nó là **mép của
   cấu trúc giá**: chỗ thị trường đã từng quay đầu ít nhất 2 lần.
2. Người ta vẽ ít lắm — thường 1 line mỗi phía, vì mỗi line phải là
   *mép đang có tác dụng* của cấu trúc mới nhất, không phải line nào
   "điểm cao" nhất.
3. Đo trên golden: đúng vậy — chọn line có neo **mới nhất** đoán trúng
   gấp 3–5 lần chọn line nhiều touch nhất.
4. Level là **trí nhớ**: giá từng bị đỡ sẽ bị đỡ lại — em đo trên 6 năm
   dữ liệu DESIGN, giá quay về đúng vùng đó thì 88% bật về phía được
   đỡ, và càng nhiều lần đỡ thì bật càng mạnh.
5. Engine hiện tại đoạn nào cũng đúng chất Volman: tease vs break,
   break xong biến thành level, zone thay vì vạch mỏng.
6. Nhưng nó **chặn quá chặt lúc sinh line**: chỉ 22% line golden được
   phép tồn tại — chủ yếu vì luật "không pivot nào được lố line".
7. Và nó **không ổn định**: nhiễu 0.3 pip làm mất nửa số line đúng —
   người thật không redraw vì wick nhích 0.3 pip.
8. Em đề xuất 5 thí nghiệm nhỏ (cờ hết, không đụng ruler): nới veto
   thành penalty, chọn theo "mép mới nhất", snap anchor vào lưới zone,
   re-anchor thành ink mới thay vì sửa lén, level chỉ sinh ở origin
   gần nhất.
9. Cái máy có thể hơn người: **nhất quán** — cùng dữ liệu phải ra cùng
   line; hiện engine deterministic tốt nhưng chưa chịu nhiễu.
10. Chi tiết + số liệu + chỗ nào không đo được: file này, mục E3/E4.
