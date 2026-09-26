# PRACTICE_ATLAS — how professionals draw and recognise price action

Lane: **PA-ATLAS** (Ruling 74, 2026-09-23 06:35Z, 8h).
Evidence base: 39 verified sources ingested into NotebookLM notebook
`Price Action` (`pa`, id de998a77-…, private) — 4 structured chat
conversations × ~5 questions each, raw answers + citations in
`nlm_raw/*.json|.md`. Source catalogue: `SOURCES.csv` (63 rows; rows
marked `fail` could not be ingested — see NOTEBOOK.md).

**How to read this file.** A rule is *consensus* only when ≥3
independent expert families agree. "Volman" here means the public
record of his method (community threads S32–S35, since his book text
cannot be uploaded) — treated as one practitioner among many, NOT as
ground truth. Osler 2000 (S18) measured inter-expert agreement on
published S/R levels at ~30%: matching ONE person's ink has a hard
ceiling, exactly as DR-BOX found (≈30% on Volman's own drawings).

Tier legend: T1 published/verifiable practitioner or peer-reviewed;
T2 reputable educator/long thread; T3 community. Source ids S01–S63
map to SOURCES.csv.

---

## O1 — Trading ranges / boxes / consolidation

### Consensus rules (≥3 families agree)

| # | Rule | Who supports (sources) |
|---|------|------------------------|
| B1 | A range = temporary equilibrium with a defended top and bottom; price reacts at edges because of anchoring + clustered orders | Wyckoff/Fraser S12–S14, Brooks S24/S27/S29, Beggs S36–S37, Kavajecz-O/W S23, Osler S18 |
| B2 | Edges are zones/bands, not pixel lines: core = cluster of closes/bodies, envelope = wick extremes | Beggs S36, Rayner S42–S43, chartmini S46, proptradingvibes S45, Volman-thread S33 |
| B3 | Birth needs ≥2 defended reactions per side (3 better); a single poke is a guess | Rayner S42, AntiVestor S44, Bulkowski rectangles S08/S09 (≥5 extrema, tops within ~0.75–1.5% band), LMW S20 (5 alternating extrema) |
| B4 | Wyckoff/event anchoring: range edges = stopping-action events (climax extreme + automatic reaction), later confirmed by secondary tests | Fraser S12–S14, StoicFX S55, Investopedia S57, T-A-P S56 |
| B5 | A poke that closes back inside is a test, not a break (springs/upthrusts are features of range edges) | Beggs S37/S39, Wyckoff S13/S55, Rayner S42, Volman-thread S35 |
| B6 | Range death = decisive close beyond edge + failure to re-enter; failed breakout at one edge tends to run to the opposite edge | Brandt S05/S06, Beggs S39, Brooks S27, Bulkowski S08 |
| B7 | Economy: keep very few objects; delete stale/broken structure immediately | Brandt S05–S07 (15-second / ≤4-lines rule), Rayner S42 (1–2 zones around price), prop desk S45 (3–5 zones), Brooks S25 |

### Disputed rules

| # | Dispute | Positions |
|---|---------|-----------|
| BD1 | Wick vs body edges | Wick envelope: Grimes S01 (wicks only for lines), classical. Body/close edges: Brooks S24 (bodies often clearer), prop desk S45 (bodies core + wick outer). Middle: two-layer zones S45/S46. |
| BD2 | Does a range need a preceding climax event? | Wyckoff S12–S14: yes (SC+AR define it). Brooks/Volman: a quiet sideways block after any leg suffices (S25, S35). Bulkowski/LMW: pure geometry suffices (S08, S20). |
| BD3 | Fixed-timeframe ranges vs "the range you need now" | HTF-priority school S42/S45/S51 vs session-priority school (Volman/Brooks intraday: freshest local structure matters most, S27/S35). |

### Machine-ready candidates (boxes)

**BX-1 — Event-anchored edge seed (Wyckoff birth channel).**
(a) A box's far edge may be seeded by the largest-range "climax" bar in
the lookback, not only by clustered extremes.
(b) Causal: at bar `i`, let `j = argmax_{s<=k<=i} (h_k - l_k)` with
`h_k-l_k >= 1.5*ABR`; seed top edge at `h_j` (or bottom at `l_j` for
accumulation shape) if ≥2 bars within `tol` of `h_j` exist and a
contained close-run of ≥`min_build_bars` follows. O(bars) per eval.
(c) Fraser S12–S14, StoicFX S55, T-A-P S56 (T1/T2). Also matches
DR-BOX's own suggestion of "a second birth channel for
session/episode containers".
(d) Engine status: **missing** — `_propose_window` only clusters
window highs/lows (boxes.py:129-132); `asia_update` (1067+) is the
only event-channel. Add as third birth route beside
`congestion_scan`/`_pivedge_emit`.
(e) Variants: V1 `climax_mult=1.5, min_witnesses=2`; V2 `1.8,3`.
Expected: box@1 +reach (DR-BOX: 68/119 goldens unreachable — this
targets that gap); clutter neutral (still budgeted by salience).

**BX-2 — Opposite-edge run after failed breakout.**
(a) When a box edge is poked and closes back inside (tease), the
opposite edge becomes the operative target — mark the event, don't
kill the box.
(b) Causal: on bar `i`, if `h_i > top + tease` and `c_i < top`, emit
event `failed_break_up`; box stays alive; `salience` may then prefer
bot-side plays. Cheap: reuses `_break_class` inputs (boxes.py:1290).
(c) Beggs S39 (stretch/BOF→opposite edge), Wyckoff spring S13/S55,
Volman-thread S35, Raschke turtle-soup S30. Strong multi-family.
(d) Engine: **partially follows** — `_break_class` (1290+) classifies
breaks and `tease_tol` exists; opposite-edge targeting is **missing**
(no event→edge linkage found).
(e) Variants: V1 event only (`tease` mark + retarget flag); V2 also
extend box TTL by `extend_on_tease_bars=24`. Expected: box@1 small +,
clutter neutral; mainly helps downstream trade logic, not the ruler.
Low priority for ruler gain.

**BX-3 — Tight-core edge preference (already implemented — verify).**
Corpus agrees golden-style boxes are the *tight core* of congestion
(S45/S46 core-vs-envelope, S08 band tolerance). Engine already scans
opposite clusters "tightest first" (boxes.py:168-181) — **follows**;
no variant needed. Listed to record the consensus.

---

## O2 — Sloped trend lines / channels

### Consensus rules

| # | Rule | Who supports |
|---|------|--------------|
| L1 | Up-line sits *under* price connecting higher lows; down-line *over* price connecting lower highs; slope direction is a hard constraint | Grimes S01–S02, Sperandeo S11/S47, DeMark S16–S17, AmiBroker S59, Brooks S24 |
| L2 | Anchors are meaningful swing extremes; ≥2 anchors birth, 3rd touch confirms | Grimes S01, AmiBroker S59, DeMark S16, Rayner S43 |
| L3 | **The line must not cut through prices between its anchors** | Grimes S01–S02 (explicit "sloppy practice" warning), Sperandeo S11/S47, Brandt/E&M S05–S06 |
| L4 | Wick pokes that close back inside are tests, not breaks; decisive break needs a *close* beyond (E&M: ~3% or clear momentum; on FX scale ≈ `>tol` close) | Brandt S05 (E&M 3 tests), Beggs S36–S39, Rayner S42, DeMark qualified-break S16–S17 |
| L5 | The operative line is the defended edge of the *newest* structure; redraw when a new extreme extends the move (re-anchor to the low preceding the new high) | Sperandeo S11/S47 (fan rule), Grimes S02, Brooks S24/S29 (micro→broad lines), DeMark S16 (most recent TD points) |
| L6 | A revision is new ink / an event, not a silent mutation | Sperandeo fan S11, DeMark re-anchoring S16, Brandt discard-broken S05–S06; corpus zones S46 "version control" |
| L7 | Broken lines may carry forward as horizontal levels (role reversal / neckline behaviour) | Beggs S37–S38, Rayner S42–S43, Brooks S27, SMC/BOS S53 |

### Disputed rules

| # | Dispute | Positions |
|---|---------|-----------|
| LD1 | Do diagonal lines even work? | Brandt S05–S07: diagonals are the *least* reliable construction, horizontals carry targets, diagonals don't; prop desk S45 dropped TLs entirely. vs Brooks S24/S29 (lives on TLs/channels), Grimes S01 (strict rules make them usable), DeMark S16. |
| LD2 | Wick vs body anchors | Grimes S01: wicks only, body-cutting invalidates. Brooks S24: bodies sometimes better. Rayner S43: whichever maximises touches. |
| LD3 | Touch count: more = stronger or weaker? | Classical S59/S16: 3rd touch validates. Order-flow school S39/S45 & Raschke S30: each retest thins resting orders; 4th–5th touch likelier to break. Resolution used below: **touches confirm the edge's existence; they do not predict the next hold.** |
| LD4 | Steep micro lines vs flat broad lines | Brooks: steep micro-TLs for momentum/flags (S24/S29). Brandt/Grimes: prefer the structural line; steep lines morph (S05, S02). |

### Machine-ready candidates (lines)

**LN-1 — Operative-edge selection = freshest anchor pair (already queued L-1, now multiply-confirmed).**
(a) Among legal lines, prefer the one whose first anchor is newest
(the current structure's defended edge), not the max-touch fit.
(b) Causal: `key = (-pa.t_ext … )` as in `rank=="young_a"`
(lines.py:265-270). O(pairs) as today.
(c) Grimes S02, Sperandeo S11, Brooks S24/S29, DeMark S16 — 4 T1
families, strongest consensus in the corpus.
(d) Engine: **follows** behind flag `line.rank=young_a` (lines.py:136,
265-270); default still touch-score.
(e) No new variant — R73 already queues L-1; atlas adds multi-expert
weight. Expected line@2 + (L-1 measured in lab), clutter neutral.

**LN-2 — Wick-poke survival / close-only veto (L-1 companion).**
(a) An in-span wick past the edge does not veto birth; only a close
beyond `k*tol` does.
(b) `over_veto_mode="close_only"`, `over_veto_tol_mult≈2`
(lines.py:201-232). Causal, O(span).
(c) Brandt S05 (E&M close test), Beggs S39, Rayner S42, Wyckoff
springs S13 — consensus that penetration ≠ break.
(d) Engine: **follows** behind flag (default `hard`).
(e) Variants already specified in R73 L-1. Expected line@2 +reach.

**LN-3 — Anchor snap to tolerance grid (L-4).**
Corpus: edges are zones (S42/S45/S46); snapping anchors to a
`anchor_snap*tol` grid (lines.py:140) implements "zone-stable
anchors". **Follows** behind flag. Expected: stability, fewer
phantom re-anchors.

**LN-4 — Revision-as-ink (L-3).**
Re-anchor closes incumbent and births sibling (`reanchor_ink`,
lines.py:343-350) — corpus L6. **Follows** behind flag.

**LN-5 — Channel return line (new, small).**
(a) With a valid trend line, also draw the parallel line through the
largest intervening opposite-side pivot.
(b) Causal: given line (pa,pb), `pc = argmax opposite-dir deviation in
(pa.t_ext, pb.t_ext)`; return-line anchor = pc; must not cut prices
either (Grimes S02 explicit). O(span).
(c) Grimes S02, Brooks S24, classical S59 — moderate consensus;
channels ARE a core pro object our engine lacks.
(d) Engine: **missing** — LineBook emits single lines only.
(e) Variant V1 only: emit `CONTEXT_LINE` sibling parallel at `pc`,
same death rules. Expected line@2 ±small, clutter +1 object unless
budgeted — cap via salience. Medium-low priority.

**LN-6 — Touch-saturation penalty (disputed — flag only).**
(a) In *selection scoring*, cap touch benefit at 3 defended touches;
don't penalise birth.
(b) `score = min(nt,3)` in the `key` (lines.py:258).
(c) Order-flow school S39/S45/S30 vs classical S59/S16 — genuine
disagreement (LD3).
(d) Engine: **violates** the order-flow view (max-touch wins by
construction); matches classical view.
(e) V1 `touch_cap=3`. Expected line@2 unclear (could cut either way) —
that is exactly why it must stay a flagged experiment.
⚠ Marked **disputed**, not consensus; also tension with DR-LINE
"more defended touches strengthen the edge" — see §CONTRA.

---

## O3 — Horizontal levels / zones

### Consensus rules

| # | Rule | Who supports |
|---|------|--------------|
| H1 | Levels are zones: core at close-cluster, envelope to wick extreme | Beggs S36–S38, Rayner S42–S43, S45, S46, S60 |
| H2 | Seeds: obvious swing extremes, session/day reference points (PDH/PDL, ON H/L, Asia H/L), breakout origins, round numbers (00/50) | Beggs S37, Rayner S42, prop S45, Osler S19 (order clustering at 0/5 endings; >70% of published levels end in 0), Brooks S26 (magnets), YTC-structure S40 |
| H3 | ≥2 reactions to birth; quality (sharp rejection) > raw count | Rayner S42, AntiVestor S44, Grimes S03, Garzarelli S21 (bounce prob rises with prior bounces) |
| H4 | Levels decay with age and with each test (order thinning); prune stale | S45, S39, arXiv S22 (bounce prob decays with age), Raschke S30 |
| H5 | Role reversal: broken support ↔ resistance; the retest of the break point is the trade location | Beggs S36–S38, Rayner S42–S43, Brooks S26–S27, SMC BOS/CHoCH S53, Volman-thread S34–S35 |
| H6 | Economy: ~3–6 zones per instrument/timeframe, nearest to price matter most | Brandt S05–S07, prop S45, Rayner S42, S60, Osler S18 (firms publish 2.5–18/day) |

### Disputed rules

| # | Dispute | Positions |
|---|---------|-----------|
| HD1 | Line vs zone vs two-line | Rayner: 1 line if tight respect, 2 if zone (S42). Beggs/prop: always zones (S36/S45). Grimes: most levels are noise anyway (S03). |
| HD2 | HTF primacy vs freshest-local | HTF school S42/S45/S51 vs intraday-freshest S35/S27. On M5 scalp charts both agree session/Asia extremes dominate. |

### Machine-ready candidates (levels)

**LV-1 — Level birth = nearest defended origin (already queued L-2; corpus-backed).**
(a) Birth a level at the price of the most recent *defended* swing
origin (a pivot that produced a ≥k·ABR reaction), not merely at
window extremes.
(b) `defended_origin` flag path already exists
(levels.py:92-110, `_add_origin` 235+, `_def_birth` 400+).
(c) Beggs S37 (level = defended origin / trapped-trader memory),
Brooks S26 (breakout origins = magnets), S45. T1+T2 consensus.
(d) Engine: **follows** behind flag.
(e) Variants already in R73 L-2. Expected level@1 +.

**LV-2 — Age decay + retest-thinning for live levels.**
(a) A level's salience decays with time-since-last-defence and after
~3 defended tests.
(b) Causal: `score *= exp(-(i - last_defence)/tau)` and
`*= 1` for `n_def<=3` else `thin_w`; `tau≈2 sessions` on M5
(from S22 decay + S45 ~2-week pruning scaled). O(1)/bar.
(c) arXiv S22 (decay), Beggs S39 (stretch/exhaustion), S45, Raschke
S30. Moderate-strong consensus.
(d) Engine: **partially** — `_expire_sweep` (levels.py:268) prunes on
time; retest-thinning absent in `_live_score` (288).
(e) V1 `tau=2*session_bars, thin_w=0.7 after 3 defs`; V2 `tau=4
sessions, thin_w=0.5`. Expected level@1 +, clutter − (faster prune).

**LV-3 — Round-number proximity bonus (small).**
(a) `+rn_bonus` to level salience when `|price mod 50 pips| <= tol`.
(b) O(1). Causal.
(c) Osler S19 (measured clustering), S45/S42 mention, Brooks S26
(100-interval magnets). Consensus moderate; spec says round grids are
context, not structure (VOLMAN spec §2) — so **bonus only, never a
standalone level**.
(d) Engine: **missing** (no rn term in `_live_score`).
(e) V1 `rn_bonus=0.25`, grid 50 pips; V2 0.15, grid 100. Expected
level@1 +tiny. ⚠ DR-BOX rejected round numbers as *box selectors* —
this is a level salience prior, a different (weaker) claim; keep
flagged.

**LV-4 — Role-reversal carry (verify coverage).**
Broken box edge/line → opposite-side level already routes via
`spawn(route=…, src=…)` (levels.py:33-83) and lines.py pierce→level
conversion (docstring l.10-11). Corpus H5 consensus. **Follows**; no
variant.

---

## O4 — Pattern marks (DT/DB, wedge, flag, squeeze, failed breakout, tease)

### Consensus rules

| # | Rule | Who supports |
|---|------|--------------|
| P1 | Double top/bottom = two same-price extrema (within ~1.5% / `tol` band) separated by an intervening reaction; **born on 2nd test, confirmed only on close past the middle peak/trough** | Bulkowski S10, LMW S20, Brooks S24, Brandt S06 |
| P2 | Unconfirmed pattern is not a pattern — "squiggles" until the confirmation close (Bulkowski: ~48% of unconfirmed DBs never confirm) | Bulkowski S10, Brandt S05–S06 |
| P3 | Wedge = 3 pushes in a converging channel (Brooks); confirms on break of the counter-slant boundary | Brooks S24/S29, Bulkowski rank table, Brandt morphology warning S05–S06 |
| P4 | Flag = impulse leg + shallow counter consolidation (1–10 bars / micro-line); confirms on trend-side break | Brooks S24/S29, Raschke S30, Bulkowski |
| P5 | Failed breakout / spring / tease = poke beyond edge + close back inside; marks trapped-side liquidity event | Wyckoff S13/S55, Beggs S39, Raschke S30, Volman-thread S35 |
| P6 | Squeeze/compression = progressively shallower pullbacks into an edge (buildup) — pre-breakout tension marker | Volman-thread S32/S35, Rayner S42 (buildup), Brooks S25 |

### Disputed rules

| # | Dispute | Positions |
|---|---------|-----------|
| PD1 | Fixed geometry vs dynamic structure | Bulkowski/LMW: rigid filters (S10, S20). Wyckoff S55: "market never behaves the same way twice" — events not shapes. Brandt: patterns morph (S06). |
| PD2 | Mark unconfirmed patterns at all? | Classical: no ink before confirmation (S10, S05). Volman/Brooks scalping: the *setup* is drawn pre-break as trade location (S35, S25). Our engine follows the scalping convention (tease/buildup marks). |

### Machine-ready candidates (patterns)

**PT-1 — Double-top/bottom event mark (born on 2nd touch, confirm on middle-peak break).**
(a) Emit a `PATTERN` mark when two same-side pivots sit within `tol`
with an intervening opposite pivot ≥`k_mid*ABR` away; upgrade to
"confirmed" on close past the middle extreme.
(b) Causal: scan confirmed pivot stream; `|p1-p2| <= tol`,
`mid = max opposite pivot between`; heights in ABR units. O(pivots).
(c) Bulkowski S10 (≥10% peak on dailies → scale to `k_mid≈0.8*ABR`
on M5), LMW S20 (1.5% band → `tol`), Brooks S24. Strong consensus.
(d) Engine: `patterns.py` exists — check coverage; DT/DB *event*
marks appear **missing/partial** (no dedicated object type found in
engine.py scan).
(e) V1 `k_mid=0.8, band=tol`; V2 `k_mid=1.2, band=1.5*tol`. Expected:
ruler gains only if golden marks count — likely INFO-level;
clutter +small, budget it.

**PT-2 — Failed-breakout/spring event (shared with BX-2).**
See BX-2 — same mechanism, emitted as a `tease`/`spring` event mark
rather than a box property. Consensus strong (P5).

---

## Rule × expert matrix (agree / disagree / silent)

`A`=agree `D`=disagree `s`=silent. Columns: Grimes, Brandt, Bulkowski,
Wyckoff(Fraser+school), DeMark, Brooks, Beggs(YTC), Rayner, Raschke,
Academic(Osler/LMW/Garzarelli/arXiv/K-OW), Community(Volman threads,
SMC, prop).

| Rule | Gri | Bra | Bul | Wyk | DeM | Bro | Beg | Ray | Ras | Acd | Com |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| Edges are zones not lines | s | A | A | A | s | A | A | A | s | A | A |
| ≥2 defended reactions to birth | A | A | A | A | A | A | A | A | s | A | A |
| Poke+close-inside = test not break | s | A | A | A | A | A | A | A | A | s | A |
| Newest structure is operative | A | s | s | s | A | A | s | s | s | s | A |
| Re-anchor = new ink/event | s | A | s | s | A | s | s | s | s | s | A |
| Line must not cut prices | A | A | s | s | s | s | s | s | s | s | A |
| Levels decay / thin on retests | s | s | s | s | s | A | A | s | A | A | A |
| Round numbers attract orders | s | s | s | s | s | A | A | A | s | A | A |
| Role reversal after break | s | s | s | A | s | A | A | A | s | s | A |
| Diagonals unreliable vs horizontals | D | A | s | s | s | D | s | s | s | s | A |
| Wick-only anchors | A | s | s | s | A | D | s | D | s | s | s |
| Climax-event anchors a range | s | s | s | A | s | D | s | s | s | s | s |
| Patterns need confirmation close | s | A | A | s | s | s | s | s | s | A | s |
| ≤~5 objects, prune stale | A | A | s | s | s | A | A | A | A | s | A |

## Ranking (expected ruler gain × consensus strength)

1. **LN-1 operative=freshest** (L-1) — 4×T1 consensus; directly fixes
   the line@2 selection weakness DR-LINE measured.
2. **LN-2 close-only veto** — consensus P/edge-survival; unlocks
   reach lost to hard veto.
3. **LV-1 defended-origin birth** (L-2) — consensus H2/H5; targets
   level@1 reach.
4. **LV-2 decay+thinning** — consensus H4; level@1 + clutter −.
5. **BX-1 climax-edge birth channel** — Wyckoff consensus + DR-BOX's
   own suggestion; targets the 68/119 unreachable gap.
6. **LN-3/LN-4** (L-4/L-3) — already queued; stability & honesty.
7. **PT-1 DT/DB marks** — consensus but low ruler weight.
8. **LV-3 round-number bonus** — weak/moderate; flag only.
9. **LN-5 channel return line** — real pro object, medium effort.
10. **LN-6 touch-saturation** — disputed; research only.

## CONTRA — conflicts with DR-BOX / DR-LINE

- **LN-6 vs DR-LINE**: DR-LINE E-sections read defended touches as
  *strengthening* the edge. The order-flow school says each retest
  *thins* the orders. Both can be true (edge more real, next test
  more likely to break) — but any touch-saturation **selection**
  penalty is a disputed experiment, not atlas consensus. Flagged.
- **LV-3 vs DR-BOX**: DR-BOX rejected round-number *box selection*.
  LV-3 is a level *salience prior*, weaker claim, different object.
  Kept flagged, low rank.
- **BX-1 vs DR-BOX**: not a contradiction — DR-BOX explicitly floated
  a second birth channel for episode containers; BX-1 is that
  channel with Wyckoff consensus behind it. Note DR-BOX also warned
  narrative frames can't be recovered from geometry — BX-1 uses a
  *mechanical* climax proxy (largest-range bar), not the narrative.
- **LD1 (Brandt: diagonals unreliable) vs our line-heavy engine**:
  recorded as a school-level disagreement, not an engine change.
  Grimes/Brooks/DeMark provide the counter-position with mechanical
  rules the engine already approximates.
- **PD2 (confirmation before ink) vs scalping convention**: classical
  sources want no unconfirmed ink; Volman/Brooks draw setups
  pre-break. Engine follows the scalping convention — noted, not
  changed.

## What could NOT be reached (honesty section)

- Forex Factory threads (Cloudflare blocks both webfetch and
  NotebookLM ingest): Volman coverage relies on Trade2Win thread
  S35 + secondary sources.
- brookstradingcourse.com articles: crawler-blocked; Brooks covered
  by his 3 YouTube videos instead (S24/S28/S29).
- Reddit: reddit.com 403 to fetcher; only S61/S62 via GitHub mirrors.
- X/Twitter: no public read path without an account — Brandt's X
  content represented by his blog/video (S05–S07). Stated plainly:
  **no X-native sources in this atlas.**
- Discord: private by design; nothing used.
- BabyPips: NLM ingest failed; pivot-point material represented via
  S49/S50 catalogue rows only (verified by search, unread in full).

---

## E5 - Tom tat cho anh

1. Các chuyên gia đồng ý gần như tuyệt đối: cạnh của hộp và vùng hỗ trợ/kháng cự là **vùng**, không phải vạch mảnh.
2. Muốn vẽ được một cạnh thì cần **ít nhất 2 lần giá bị bật lại** ở đó; 1 lần chạm chỉ là phỏng đoán.
3. Wick xuyên qua cạnh rồi đóng cửa quay lại bên trong **không phải** phá vỡ — đó là cú test (spring/tease).
4. Đường trendline đúng chuẩn **không được cắt xuyên thân nến** giữa hai điểm neo — Grimes và Sperandeo đều nhấn mạnh.
5. Đường/đối tượng **mới nhất** thường là thứ quan trọng nhất — đúng hướng L-1 mà DR-LINE đã chỉ ra.
6. Mỗi lần giá test lại một vùng, lệnh chờ ở đó **mỏng dần** — vùng bị test 4–5 lần dễ vỡ hơn vùng mới.
7. Vùng sinh ra từ **điểm xuất phát được bảo vệ** (swing bị bật mạnh, điểm breakout, session high/low) — đúng hướng L-2.
8. Wyckoff neo cạnh hộp vào **các sự kiện** (climax + automatic reaction) — gợi ý kênh sinh box mới BX-1, khớp ý tưởng DR-BOX đã ghi.
9. Pro giữ chart **rất ít đối tượng** (3–6 vùng/đường) và xoá ngay thứ đã vỡ — engine ta đã theo đúng nguyên tắc này.
10. Điểm mâu thuẫn lớn nhất: Brandt coi đường chéo **kém tin cậy** còn Brooks/Grimes/DeMark vẫn dùng có quy tắc — cả hai phía đều đã ghi vào atlas.
