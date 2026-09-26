# DR-RULES-S1 — box shape transforms (R78 §78.4(2))

Read-only estimate on the canonical C-3 arm (`uip2_pbbirth
@8361fe85e73f9437`, 623 windows, 456 golden-decision τ events).
Same replay path as DR-RULES Part D: `snapshot.live_records` +
`recall_at_k.rank_live` on cached pickles, per-family budgets
(box@1 line@2 level@1 bracket@1).  Every live BOX object at every
golden-decision τ gets the transform; the transformed object sits
in the same pick slot; ranking/scores untouched.  Written 09:33Z.

## Arms (fixed, no tuning)

- **S1-a left-edge reset.** t_left → first bar after the last
  impulse run (≥4·ABR20 net move within ≤6 consecutive
  same-direction bars) or shock bar (range ≥3·ABR20) inside the
  drawn span [t_left, τ].  Edges unchanged.  If fewer than 3 bars
  remain, the object is dropped (freed slot refilled by the
  next-ranked box).
- **S1-b age cap.** t_left → max(t_left, τ − 75 bars) — the
  author's drawn-width q95 from DR-RULES (75.4 bars ≈ 377 min,
  applied as 375 min).  Edges unchanged; never drops.

Both transforms use bars ≤ τ only.  Prefix invariance: 178/178 identical reset points when computed on the τ-clipped pickle vs the full-window pickle truncated to τ (20 panels).

## 1. Hits and keep rule

| arm | box hits | line | level | bracket | clutter (census) | keep rule |
|---|---|---|---|---|---|---|
| parent | 16 | 20 | 7 | 29 | 4.33 | — |
| S1-a reset | 15 (−1, +0) | 20 | 7 | 29 | 4.33 | FAIL (box 15<16) |
| S1-b age cap | 16 (−0, +0) | 20 | 7 | 29 | 4.33 | PASS |

Non-box hits were recomputed, not assumed: line 20, level 7,
bracket 29 under both arms (only box records are transformed,
per-family budgets make the rest identical by construction).
Clutter = published census (objects visible in window ÷ scorable
goldens, panel median).  S1-b never drops → 4.33; S1-a drops 54 object-events (909 live-box-events scanned, 5.9%) across 37 events; 10 objects are dropped at every τ where live (census effect nil at the median).

## 2. Owner-clean rate on C-3 box picks

Fraction of box@1 picks passing each Owner rule, before vs after
(hits = the 16 parent-matched picks; non-hits = 440 unmatched picks).  For S1-a the after-set has 439 picks (drops refill from lower-ranked boxes; a pick slot is empty only if every live box dropped).

| rule | hits 0 | hits S1-a | hits S1-b | non-hits 0 | non-hits a | non-hits b |
|---|---|---|---|---|---|---|
| C1@1.0 | 16/16 | 15/15 | 16/16 | 406/440 | 387/424 | 406/440 |
| C3w@3.0 | 7/16 | 15/15 | 9/16 | 163/440 | 424/424 | 236/440 |
| C4w@4 | 9/16 | 15/15 | 12/16 | 134/440 | 424/424 | 256/440 |
| C6g | 1/16 | 1/15 | 2/16 | 4/440 | 42/424 | 15/440 |
| C5@q95 | 1/16 | 7/15 | 16/16 | 18/440 | 277/424 | 440/440 |

C6g tolerance = 3 pips (mid-ruler ±3 p edge tolerance; engine
objects carry no golden label tolerance).  C1 is unaffected by
left-edge moves (same band, same τ).

All live boxes (not only picks), non-hit+hit pooled:

| rule | 0 | S1-a | S1-b |
|---|---|---|---|
| C1@1.0 | 671/909 | 621/855 | 671/909 |
| C3w@3.0 | 387/909 | 855/855 | 511/909 |
| C4w@4 | 379/909 | 855/855 | 588/909 |
| C6g | 66/909 | 70/855 | 47/909 |
| C5@q95 | 161/909 | 580/855 | 909/909 |

(S1-a evaluates only the 855 non-dropped object-events.)

## 3. Per-hit table (16 parent hits)

| panel | golden | arm | IoU 0→1 | coverage 0→1 | d_lo | d_hi | result |
|---|---|---|---|---|---|---|---|
| 9.11a | gi0 | a | 0.00→0.93 | 1.00→0.93 | 0.1 | 0.3 | kept |
| 9.11a | gi0 | b | 0.00→0.57 | 1.00→1.00 | 0.1 | 0.3 | kept |
| 9.13a | gi1 | a | 0.00→0.00 | 1.00→1.00 | 4.4 | 1.4 | kept |
| 9.13a | gi1 | b | 0.00→0.21 | 1.00→1.00 | 4.4 | 1.4 | kept |
| 9.15b | gi0 | a | 0.00→0.00 | 0.92→0.92 | 0.4 | 0.0 | kept |
| 9.15b | gi0 | b | 0.00→0.30 | 0.92→0.92 | 0.4 | 0.0 | kept |
| 9.17a | gi1 | a | 0.00→0.00 | 1.00→1.00 | 1.6 | 1.2 | kept |
| 9.17a | gi1 | b | 0.00→0.24 | 1.00→1.00 | 1.6 | 1.2 | kept |
| 9.18a | gi0 | a | 0.00→0.00 | 1.00→1.00 | 2.6 | 2.2 | kept |
| 9.18a | gi0 | b | 0.00→0.00 | 1.00→1.00 | 2.6 | 2.2 | kept |
| 9.27a | gi0 | a | 0.00→0.00 | 1.00→1.00 | 0.2 | 0.6 | kept |
| 9.27a | gi0 | b | 0.00→0.36 | 1.00→1.00 | 0.2 | 0.6 | kept |
| 9.32a | gi0 | a | 0.00→0.97 | 0.99→0.97 | 0.0 | 1.1 | kept |
| 9.32a | gi0 | b | 0.00→0.00 | 0.99→0.99 | 0.0 | 1.1 | kept |
| 9.32a | gi1 | a | 0.00→0.09 | 1.00→1.00 | 1.3 | 0.0 | kept |
| 9.32a | gi1 | b | 0.00→0.00 | 1.00→1.00 | 1.3 | 0.0 | kept |
| 9.34a | gi1 | a | 0.00→0.00 | 1.00→1.00 | 0.0 | 1.3 | kept |
| 9.34a | gi1 | b | 0.00→0.07 | 1.00→1.00 | 0.0 | 1.3 | kept |
| 9.41b | gi0 | a | 0.00→0.43 | 1.00→1.00 | 2.8 | 0.4 | kept |
| 9.41b | gi0 | b | 0.00→0.31 | 1.00→1.00 | 2.8 | 0.4 | kept |
| 9.44b | gi1 | a | 0.00→0.06 | 1.00→1.00 | 0.0 | 1.4 | kept |
| 9.44b | gi1 | b | 0.00→0.00 | 1.00→1.00 | 0.0 | 1.4 | kept |
| 9.45a | gi0 | a | 0.02→0.89 | 0.89→0.89 | 1.2 | 0.5 | kept |
| 9.45a | gi0 | b | 0.02→0.02 | 0.89→0.89 | 1.2 | 0.5 | kept |
| 9.58a | gi2 | a | 0.00→NA | 1.00→NA | 0.0 | 0.0 | dropped(<3 bars) |
| 9.58a | gi2 | b | 0.00→0.11 | 1.00→1.00 | 0.0 | 0.0 | kept |
| 9.61b | gi2 | a | 0.00→0.08 | 1.00→1.00 | 0.9 | 0.1 | kept |
| 9.61b | gi2 | b | 0.00→0.16 | 1.00→1.00 | 0.9 | 0.1 | kept |
| 9.6a | gi0 | a | 0.00→0.00 | 0.98→0.98 | 1.8 | 0.7 | kept |
| 9.6a | gi0 | b | 0.00→0.00 | 0.98→0.98 | 1.8 | 0.7 | kept |
| 9.7b | gi0 | a | 0.00→0.22 | 1.00→1.00 | 2.3 | 2.5 | kept |
| 9.7b | gi0 | b | 0.00→0.07 | 1.00→1.00 | 2.3 | 2.5 | kept |

Match mechanics (why hits survive): C-3 boxes carry no recorded
build window, so the ruler scores them by the coverage route —
golden containment window ≥50% covered by the drawn span, plus
edges within label tolerance.  Both transforms move only the
drawn LEFT edge; coverage survives while the new edge stays
before the golden window.  IoU (shown for shape, not the match
route) jumps ~0→0.4–0.97 under S1-a: the span actually tightens
to the congestion.  The single loss (S1-a, 9.58a) is a drop, not
an edge/IoU failure.

## 4. How the author's boxes start (refutation check)

Of 122 golden box-family objects: 38 have no impulse run/shock bar at all before t0 in the day's fed bars; of the 84 that do, the t0-to-event gap is <=2 bars for 4 (4.8%), <=3 for 4, <=5 for 8; median 36 bars, p90 108.

Reading: the author does NOT typically start a box right after an
extreme event — he starts in the buildup that forms later.  S1-a
reaches a similar *shape* (the span avoids legs/shocks) by
truncation, a different mechanism.  The reset idea is supported
only as an engine-side repair, not as a model of the author's
process.

## 5. Limitations

- Selection-only estimate: the engine's birth/shape code is
  untouched; on-chart, a left-edge reset could also change later
  engine behaviour (re-anchoring, edge rewrites) which this replay
  cannot see.
- S1-a's reset point depends on the impulse/shock definitions
  (≥4·ABR in ≤6 same-direction bars; ≥3·ABR range) — thresholds
  fixed by the contract, not tuned.
- Coverage-route matching means moving the left edge can only
  lose hits via drops or by crossing the golden window's start;
  gains are possible only through refilled picks.
- C6g uses a fixed 3-pip tolerance on engine objects (they have
  no label tolerance); the strict tol_e variant is in the JSONL.
- The golden-start check uses the extreme thresholds, so it
  refutes only 'starts right after big legs', not 'starts after
  the last swing break' in general.

## Tóm tắt cho anh (6 dòng)

- S1-a (cắt mép trái sau cú sốc/impulse cuối): box-hit 16→15 (mất 1 hit do object bị xoá), nên FAIL keep-rule; nhưng vật sai của máy sạch hẳn: không-shock 37→100%, không-impulse 30→100%, hộp ≤75bar 4→65%.
- S1-b (nắp tuổi 75 bar): box-hit giữ nguyên 16/16, clutter 4.33, các họ khác y nguyên → PASS keep-rule (estimate).
- Sau S1-b: hộp ≤75bar 4→100%, không-shock 37→54%, không-impulse 30→58% — sạch một phần, không hết.
- Hai arm đều không làm mất hit vì ruler chấm bằng độ-phủ của cửa-sổ vàng — mép trái dời phải vẫn chứa vùng congestion.
- Tác giả KHÔNG bắt đầu hộp ngay sau cú sốc/impulse (chỉ 5% trong ≤2 bar, median 36 bar) — reset là cơ chế sửa của máy, không phải cách tác giả vẽ.
- Đề nghị: S1-b an-toàn để build thành flag box_max_drawn_age; S1-a cần giảm drop trước khi build (ví dụ giữ object ở dạng thu-nhỏ thay vì xoá).
## S1-a' — no-drop left-edge reset (R81 §81.4)

Identical to S1-a, except: when the reset would leave fewer than
3 bars, `t_left` is set to `tau − 2 bars` (the last 3 bars are
kept) instead of dropping the object.  Causality: bars <= tau.

### Keep rule

| arm | box hits | line | level | bracket | clutter | verdict |
|---|---|---|---|---|---|---|
| parent | 16 | 20 | 7 | 29 | 4.33 | — |
| S1-a | 15 | 20 | 7 | 29 | 4.33 | FAIL box leg (drop) |
| S1-b | 16 | 20 | 7 | 29 | 4.33 | PASS (estimate) |
| **S1-a'** | **15** | **20** | **7** | **29** | **4.33** | **FAIL box leg** |

Gained hits: none.  Lost hits: 1 — the same golden as under S1-a (`9.58a` tau=545): the pick is clamped to the last 3 bars and the golden window is no longer covered (cov 0.25).  The clamp keeps the object on the chart but cannot rescue the hit.

### Transform accounting (909 live box-events)

| kind | n | meaning |
|---|---|---|
| reset | 632 | same as S1-a (>=3 bars remain) |
| clamp3 | 54 | S1-a would have dropped; kept as 3-bar box |
| none | 223 | no impulse/shock inside span |

Events with >=1 clamped box: 37; objects whose left edge moved earlier than drawn (j1-2 < j0): 0.

### Owner-clean rates (live box-events)

| group | rule | before | after |
|---|---|---|---|
| matched/picked | C3w@3.0 | 38% (175/462) | 97% (446/462) |
| matched/picked | C4w@4 | 32% (147/462) | 98% (455/462) |
| matched/picked | C5@q95 | 5% (22/462) | 66% (305/462) |
| matched/picked | C1@1.0 | 92% (427/462) | 92% (427/462) |
| matched/picked | C6g | 1% (6/462) | 10% (47/462) |
| other live boxes | C3w@3.0 | 47% (212/447) | 94% (420/447) |
| other live boxes | C4w@4 | 52% (232/447) | 99% (443/447) |
| other live boxes | C5@q95 | 31% (139/447) | 74% (329/447) |
| other live boxes | C1@1.0 | 55% (244/447) | 55% (244/447) |
| other live boxes | C6g | 13% (60/447) | 7% (31/447) |

The kept slivers are not all clean: 45 of the 54 clamp3 boxes still contain their triggering event bar(s) (43 a shock bar, 11 an impulse leg, 9 both) — when the event ends inside the last 2 bars, tau-2 still covers it.  S1-a reached 100% C3w/C4w by deleting these objects; S1-a' reaches ~97% (matched) / ~94% (other) by shrinking them.

### Per-hit table (16 parent hits under S1-a')

| panel | tau | gi | kind | same pick | cov0 | cov1 | iou0 | iou1 | match |
|---|---|---|---|---|---|---|---|---|
| 9.6a | 600 | 0 | none | y | 0.98 | 0.98 | 0.00 | 0.00 | HIT |
| 9.7b | 540 | 0 | reset | y | 1.00 | 1.00 | 0.00 | 0.22 | HIT |
| 9.11a | 660 | 0 | reset | y | 1.00 | 0.93 | 0.00 | 0.93 | HIT |
| 9.13a | 505 | 1 | none | y | 1.00 | 1.00 | 0.00 | 0.00 | HIT |
| 9.15b | 900 | 0 | reset | y | 0.92 | 0.92 | 0.00 | 0.00 | HIT |
| 9.17a | 475 | 1 | reset | y | 1.00 | 1.00 | 0.00 | 0.00 | HIT |
| 9.18a | 515 | 0 | none | y | 1.00 | 1.00 | 0.00 | 0.00 | HIT |
| 9.27a | 600 | 0 | none | y | 1.00 | 1.00 | 0.00 | 0.00 | HIT |
| 9.32a | 478 | 0 | reset | y | 0.99 | 0.97 | 0.00 | 0.97 | HIT |
| 9.32a | 510 | 1 | reset | y | 1.00 | 1.00 | 0.00 | 0.09 | HIT |
| 9.34a | 495 | 1 | none | y | 1.00 | 1.00 | 0.00 | 0.00 | HIT |
| 9.41b | 835 | 0 | reset | y | 1.00 | 1.00 | 0.00 | 0.43 | HIT |
| 9.44b | 730 | 1 | reset | y | 1.00 | 1.00 | 0.00 | 0.06 | HIT |
| 9.45a | 350 | 0 | reset | y | 0.89 | 0.89 | 0.02 | 0.89 | HIT |
| 9.58a | 545 | 2 | clamp3 | y | 1.00 | 0.25 | 0.00 | 0.25 | lost |
| 9.61b | 895 | 2 | reset | y | 1.00 | 1.00 | 0.00 | 0.08 | HIT |

Prefix invariance: 178/178 identical (truncated vs full-window pickles, 20 panels).

### Reading

- S1-a' fixes the drop mechanism but **not** the hit loss: the
  lost golden needs a box that still covers its window; a 3-bar
  sliver cannot.  The failure is not the drop rule — it is that
  this engine box is drawn over a shock the author would never
  have boxed across.
- Net vs S1-a: identical hits (15), identical non-box hits,
  clutter unchanged at 4.33 (nothing is dropped), but 54
  objects stay on the chart as 3-bar slivers, of which 45  still contain their triggering event (the event ends inside
  the last 2 bars, so tau-2 still covers it).
  For G-REVIEW that may look worse than S1-a's empty space.
- Verdict: **INFO / fails the keep rule** (box 15 < 16).  S1-b
  remains the only arm passing M1; S1-a' is still the only arm
  that keeps ~94-97% of the E5 cleaning without deleting
  objects — useful evidence that the loss is a generation
  problem (wrong box born), not a shape-fixable one.

### Files

`DR_RULES_S1ap_{measure,report,md}.py`,
`DR_RULES_S1ap_{events,rows,hits,prefix}.jsonl`,
`DR_RULES_S1ap_summary.json`,
`DR_RULES_S1{ap,a,b}_objects.jsonl` (engine-spelling overrides
for the 12 review panels; G-KIT `--override`).

### Tóm tắt cho anh (4 dòng)

- S1-a' giữ vật trên chart (không xóa), nhưng vẫn mất đúng 1 hit
  như S1-a: hộp 3 bar không phủ được cửa sổ vàng → vẫn 15/16.
- 54 vật S1-a xóa được giữ lại thành hộp 3 bar; 45 vật vẫn chứa  nến shock/impulse gây ra reset nên có thể vẫn bị Gemini chê.
- Kết luận: lỗi nằm ở chỗ máy sinh hộp sai (vẽ qua shock), không
  phải ở quy tắc xóa — S1-b vẫn là nhánh duy nhất qua keep-rule.
## S2 — the box ends at the breakout (R82 §82.3)

Rule (fixed): first run of k consecutive closes beyond
`top+tol_e` / `bottom−tol_e` inside the drawn span [t_left,
min(t_right,tau)] closes the box at tau — removed before the
box@1 pick, sticky.  tol_e = trade_tags.tol_e (imported).
Variants k2 (k=2), k3 (k=3).  Parent = C-3 canonical 623.

### Keep rule

| arm | box hits | line | level | bracket | census | prefix | verdict |
|---|---|---|---|---|---|---|---|
| parent | 16 | 20 | 7 | 29 | 4.33 | 178/178 | — |
| S2-k2 | **2** | 20 | 7 | 29 | 3.67 | 178/178 | **FAIL box leg** |
| S2-k3 | **4** | 20 | 7 | 29 | 3.67 | 178/178 | **FAIL box leg** |

Gained hits: k2 [['9.39a', 475]], k3 [['9.39a', 475]] — the 9.39a@475 gain is a promotion: closing the top box freed the slot for a lower-ranked box that matched.  Promoted picks (hit or not): k2 9.7b@540 BOX0001->BOX0011; 9.39a@475 BOX0003->CON0005; k3 9.7b@540 BOX0001->BOX0011; 9.18a@515 BOX0001->BOX0013; 9.39a@475 BOX0003->CON0005.

### What the rule does to the engine

| measure | k2 | k3 |
|---|---|---|
| live box-events closed | 806/909 (89%) | 780/909 (86%) |
| picked box closed | 443/456 | 431/456 |
| of closed: born-broken (confirm < t_birth) | 479 (59%) | 444 (57%) |
| mean live boxes / event | 0.23 (was 1.99) | 0.28 |
| census clutter | 3.67 (was 4.33) | 3.67 |

Median confirm lands ~12-14 bars after the left edge; a closed
box had then lived ~111 bars past its breakout (p10/50/90 =
41/111/176).  More than half of all closures are born-broken:
the engine draws t_left across regions price had already left,
so the first break sits *before* the box was even born.

### Author compliance (same rule on golden boxes, own span/edges)

| k | golden boxes the rule would close | share |
|---|---|---|
| 2 | 29/122 | 24% |
| 3 | 17/122 | 14% |

The author keeps ~14% (k3) to ~24% (k2) of his boxes despite
confirmed closes beyond them inside their own drawn span — the
box documents a congestion price already left, which he still
draws.  The reviewer's literal rule is stricter than the author.

### Reviewer cases

S1-b fatal boxes (the capped rectangles):

| panel | object | closed k2 | closed k3 | confirm bar |
|---|---|---|---|---|
| 9.10c | BOX0001 | y | y | 1 / 2 |
| 9.33c | BOX0001 | n | n | — / — |
| 9.36c | BOX0001 | y | y | 1 / 2 |
| 9.40a | BOX0002 | y | y | 8 / 9 |

R1 E5 panels (box swallows impulse / lives past breakout) —
closed box-family objects in the drawn set:

- `9.17b`: BOX0001(k2 @5 dn), BOX0001(k3 @6 dn), CON0007(k2 @97 up), CON0007(k3 @98 up)
- `9.36c`: BOX0001(k2 @1 dn), BOX0001(k3 @2 dn), BOX0014(k2 @116 up), BOX0014(k3 @120 up), BOX0018(k2 @177 up), BOX0018(k3 @178 up)
- `9.42b`: BOX0001(k2 @21 up), BOX0001(k3 @22 up), BOX0012(k2 @93 dn), BOX0012(k3 @94 dn), BOX0013(k2 @105 dn), BOX0014(k2 @111 up), BOX0014(k3 @117 up)
- `9.48b`: RAN0000(k2 @95 up), RAN0000(k3 @96 up), BOX0001(k2 @6 dn), BOX0001(k3 @7 dn)

### Per-hit table (16 parent box hits)

| panel | tau | gi | arm | pick0 closed | confirm bar | bars before tau | pick | match |
|---|---|---|---|---|---|---|---|---|
| 9.6a | 600 | 0 | k2 | y | 1 | 115 | none | lost |
| 9.6a | 600 | 0 | k3 | y | 2 | 114 | none | lost |
| 9.7b | 540 | 0 | k2 | y | 2 | 102 | fill:BOX0011 | HIT |
| 9.7b | 540 | 0 | k3 | y | 3 | 101 | fill:BOX0011 | HIT |
| 9.11a | 660 | 0 | k2 | y | 1 | 127 | none | lost |
| 9.11a | 660 | 0 | k3 | y | 2 | 126 | none | lost |
| 9.13a | 505 | 1 | k2 | y | 6 | 91 | none | lost |
| 9.13a | 505 | 1 | k3 | n | None | None | same | HIT |
| 9.15b | 900 | 0 | k2 | y | 8 | 168 | none | lost |
| 9.15b | 900 | 0 | k3 | y | 9 | 167 | none | lost |
| 9.17a | 475 | 1 | k2 | y | 8 | 83 | fill:CON0007 | lost |
| 9.17a | 475 | 1 | k3 | y | 9 | 82 | fill:CON0007 | lost |
| 9.18a | 515 | 0 | k2 | y | 1 | 98 | fill:RAN0000 | lost |
| 9.18a | 515 | 0 | k3 | y | 2 | 97 | fill:BOX0013 | HIT |
| 9.27a | 600 | 0 | k2 | y | 9 | 107 | none | lost |
| 9.27a | 600 | 0 | k3 | y | 10 | 106 | none | lost |
| 9.32a | 478 | 0 | k2 | y | 2 | 89 | none | lost |
| 9.32a | 478 | 0 | k3 | y | 3 | 88 | none | lost |
| 9.32a | 510 | 1 | k2 | y | 2 | 96 | none | lost |
| 9.32a | 510 | 1 | k3 | y | 3 | 95 | none | lost |
| 9.34a | 495 | 1 | k2 | y | 5 | 90 | none | lost |
| 9.34a | 495 | 1 | k3 | y | 6 | 89 | none | lost |
| 9.41b | 835 | 0 | k2 | y | 8 | 155 | none | lost |
| 9.41b | 835 | 0 | k3 | y | 9 | 154 | none | lost |
| 9.44b | 730 | 1 | k2 | y | 33 | 109 | none | lost |
| 9.44b | 730 | 1 | k3 | y | 34 | 108 | none | lost |
| 9.45a | 350 | 0 | k2 | y | 23 | 43 | none | lost |
| 9.45a | 350 | 0 | k3 | y | 24 | 42 | none | lost |
| 9.58a | 545 | 2 | k2 | y | 2 | 103 | fill:RAN0000 | lost |
| 9.58a | 545 | 2 | k3 | y | 3 | 102 | fill:RAN0000 | lost |
| 9.61b | 895 | 2 | k2 | y | 2 | 173 | fill:RAN0000 | lost |
| 9.61b | 895 | 2 | k3 | y | 3 | 172 | fill:BOX0009 | lost |

### Reading / limitations

- S2 as specified is **far too strong**: it fires on 86-89% of
  live box-events and keeps only 2/16 (k2) / 4/16 (k3) hits.
  Both variants FAIL the keep rule (box leg).
- Mechanism: the engine's boxes have long retroactive left
  edges; ~57-59% of closures confirm *before* t_birth — the
  box is born already-broken.  This is a generation error
  (t_left drawn across an escaped region), the same lesson as
  S1-a': the fix belongs in generation, not in post-hoc
  closure.
- The rule does clean what the reviewer flagged: 3/4 S1-b
  fatal boxes close (9.10c, 9.36c, 9.40a; 9.33c does not),
  and every named box on the 4 E5 panels closes under both k.
- Author check: the author himself keeps 14-24% of boxes with
  confirmed closes beyond them — a literal 'end at breakout'
  is stricter than the author, so even a working variant would
  need an M2-vs-M1 conversation, not just a build flag.
- Offline estimate only; ranking/scores untouched; other
  families verified identical (20/7/29); prefix 178/178.

### Files

`DR_RULES_S2_{measure,report,md}.py`,
`DR_RULES_S2_{events,rows,hits,golden,prefix,census}.jsonl`,
`DR_RULES_S2_summary.json`, `DR_RULES_S2_review_closed.jsonl`,
`DR_RULES_S2_{k2,k3}_objects.jsonl` (G-KIT overrides, engine
spelling, base = review/sets/c3 drawn objects minus closed).

### Tóm tắt cho anh (5 dòng)

- S2 đóng hộp khi giá close qua mép: k2 giữ 2/16 hit, k3 giữ
  4/16 — quá mạnh, rơi keep-rule.
- Nhưng đúng bệnh: ~57-59% hộp bị đóng là 'sinh ra đã vỡ' — máy
  kéo mép trái qua vùng giá đã thoát từ trước.
- Rule đóng được 3/4 hộp S1-b bị Gemini chê và toàn bộ hộp E5 —
  vấn đề nằm ở generation, không phải lọc sau.
- Tác giả cũng giữ 14-24% hộp đã bị close vượt mép — rule literal
  còn chặt hơn cả tác giả.
- Đề nghị: không build S2; đưa 'đừng sinh hộp qua breakout cũ'
  vào nghiên cứu generation (E3/BOX-LAB).
