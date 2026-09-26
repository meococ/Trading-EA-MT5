# E3 DIAG — "the current box is missing" (R82 §82.7)

BOX-LAB, read-only, 23/09 ~13:05Z. Parent: C-3 @fa2e52e5 default flags
(canonical caches `uip2_pbbirth@8361fe85`, 623 TUNE panels — verified
canonical-identical to parent). Ruler: `eval_v2` imported. Script:
`boxlab/e3_diag.py`; rows: `boxlab/e3_diag.jsonl` (110 rows).

**Definitions (stated before measuring, in `e3_diag.py` docstring):**
- *Current at τ:* golden box drawn right edge `t1 ≥ τ − 15` (covers τ,
  open right, or ended within 3 bars).
- *Miss:* rank-1 live box-family object at τ fails `match_detail`.
- Classes (exactly one per miss):
  - `LIVE_OUTRANKED` — a live box object matches the golden but a
    different box holds rank-1.
  - `BUDGET_CUT` — the best overlapping cand (edge-matching preferred)
    was refused by the budget/rank machinery: `outranked`,
    `nms_suppressed`, `joint_capped`, `rate_limited`, `expired`
    (pool TTL), or `proposed` still pending at τ.
  - `BORN_KILLED` — an overlapping cand/object existed and was killed
    by generation gates (`below_min_score`, `vetoed_*`,
    `dedup_existing`, `route_shadow`, `uip_spent`, `uip_skip_pb`), by
    an object death event, or by the incumbent overwriting its own
    matching geometry (`overwritten_by_next_write`).
  - `NEVER_BORN` — no box-family cand overlapping the golden in time
    AND price.

## Item 1 — the 7 named panels at review τ

| panel | τ | author box current? | class | engine state near it |
|---|---|---|---|---|
| 9.10c | 945 | **none** | NO_AUTHOR_BOX | reviewer saw a congestion the author never boxed |
| 9.11b | 840 | **none** | NO_AUTHOR_BOX | same — disagreement-with-author, not an engine miss |
| 9.25a | 300 | **none** | NO_AUTHOR_BOX | same |
| 9.17b | 730 | [13244.0, 13251.0] span 660–720 | **BUDGET_CUT** | `cluster_range` cand [13242.6, 13252.2] **edge-matched**, `outranked` at cet 705 by incumbent BOX0001 [13201.6, 13208.4] (age 134b, **39.8p from price**) |
| 9.2b | 765 | [13239.0, 13261.0] span 580–810 | **BUDGET_CUT** | `cluster_range` cand [13239.8, 13259.2] **edge-matched**, sat pending then `expired` at cet 755 behind incumbent BOX0002 [13239.8, 13253.9] (age 135b; top off by 7p where cand was off by 1.8p) |
| 9.33c | 1055 | [13061.0, 13076.0] span 1000–1140 | **BUDGET_CUT** | `cluster_range_wick` cand [13060.6, 13075.1] **edge-matched**, proposed at cet 1050 — still **pending** at τ behind incumbent BOX0001 [12994.5, 13075.1] (bottom 66p too deep) |
| 9.52a | 350 | [12907.5, 12930.9] span 240–600 | **BUDGET_CUT** | `cluster_range_wick` cand [12917.7, 12930.7] pending at cet 340 (overlapping but bottom 10p off — not edge-matching); incumbent BOX0002 [12917.5, 12927.7] also wrong on bottom |

**Reading:** on 3/7 panels the reviewer flagged a congestion the
author did not box — those are author-disagreement cases, not engine
misses. On the other 4, the engine DID generate the author's geometry
as a candidate (3 of 4 edge-matched), and in every case an old
`ev_*`/UIP incumbent box held the family's single box slot, so the
correct fresh cand was `outranked`, `expired`, or left `proposed`
pending at τ.

## Item 2 — all TUNE golden box decisions (current, missed at box@1)

103 misses (119 − 16 hits). Four-way split:

| class | n | share | edge-matched cand existed | killers |
|---|---|---|---|---|
| **BUDGET_CUT** | **59** | 57% | **30/59** | proposed-pending 25, outranked 19, expired 13, rate_limited 2 |
| **BORN_KILLED** | 32 | 31% | 13/32 | below_min_score 18, overwritten_by_next_write 11, close:post_break_window 2, uip_skip_pb 1 |
| **NEVER_BORN** | 8 | 8% | — | (see item 4) |
| **LIVE_OUTRANKED** | 4 | 4% | — | 9.1c@795, 9.20c@1080, 9.36b@560, 9.39a@475 |

Examples per class:
- BUDGET_CUT: 9.2a@250, 9.2b@765, 9.2b@835, 9.2c@780.
- BORN_KILLED: 9.3b@745, 9.10c@980, 9.11c@1070, 9.12c@1020.
- NEVER_BORN: 9.7a@580, 9.18b@635, 9.22a@600, 9.47a@130.
- LIVE_OUTRANKED: all four listed above.

**43/103 misses had an edge-matching cand in the log.** The dominant
failure is NOT generation — it is **retention/incumbency**: the
`ev_uip` object holds the family's one box slot with stale geometry
(its own writes drifted), while fresh structural-path cands
(`cluster_range` 13, `cluster_range_wick` 25, `congestion_scan` 19)
propose the author's band and die waiting: pending 25, outranked 19,
expired 13, rate_limited 2. A further 11 misses are the same monopoly
inside the object: the incumbent *wrote* the matching geometry
mid-stream then rewrote it away before τ (`overwritten_by_next_write`
— the R73 youngest-write wall in object form). `below_min_score`
kills 18 more overlapping cands.

## Item 3 — S2 overlap on the 4 LIVE_OUTRANKED cases

S2 close rule: first run of k consecutive closes beyond the drawn
edges by > `tol_e` within [drawn left edge, τ].

| panel | outranker | S2-k2 closes? | S2-k3 closes? | next-ranked matches? |
|---|---|---|---|---|
| 9.1c@795 | BOX0001 (age 143b, dist 0.0p) | no | no | — |
| 9.20c@1080 | BOX0001 (age 203b) | yes (bar 140) | yes (141) | **yes** — CON0006 rank 2 |
| 9.36b@560 | BOX0001 (age 102b) | yes (bar 93) | yes (94) | no — BOX0014 [13105.6, 13133.4] would inherit @1 and does not match |
| 9.39a@475 | BOX0003 (age 68b) | yes (bar 21) | yes (22) | **yes** — CON0005 rank 2 |

**S2 estimate: closes the outranker in 3/4 (identical at k=2 and
k=3), but converts only 2/4 misses into hits** (9.20c, 9.39a) —
because in 9.36b the promoted box is also wrong, and in 9.1c the
outranker never broke. Note S2's real leverage is larger than this
table: closing the incumbent frees the family slot for the 25
pending `proposed` cands — whether they then birth is engine
behaviour DR-RULES measures, not estimable read-only.

## Item 4 — NEVER_BORN shape (n = 8)

- Width: median **25 bars** (p25 17, p75 75) — longer than typical.
- Height: median **2.6 ABR20** (p25 2.1, p75 3.7), i.e. ~11–18p.
- Distance to EMA25: median **2.35 ABR20** — mixed; 5/8 within ~1.5
  ABR.
- Failed requirements: **7/8 have no pivot pair inside the golden
  window** (the event routes have nothing to pair); 2/8 too tall for
  the 4·ABR congestion cap. By their own dims 6/8 are cong-legal —
  yet the candidate stream in those windows formed at *other* price
  bands (e.g. 9.7a: 88 cands overlap the golden's span, all
  20–30p above the golden band). The author's box is a price level
  the generator never enumerated — a true generation gap, but only
  8% of misses.

## Tóm tắt (5 dòng)

1. Lỗi E3 ("hộp hiện tại bị thiếu") KHÔNG phải lỗi generation: chỉ
   8/103 miss là NEVER_BORN; 43/103 đã có cand đúng-edge trong log.
2. 57% miss là BUDGET_CUT: cand đúng (cluster_range/_wick,
   congestion_scan) bị incumbent UIP box giữ slot — pending 25,
   outranked 19, expired 13, rate_limited 2.
3. 31% là BORN_KILLED: score-floor giết 18, và 11 case incumbent tự
   viết đúng geometry rồi rewrite mất (youngest-write wall).
4. S2 đóng 3/4 outranker nhưng chỉ cứu 2/4 outranked-miss; đòn bẩy
   thật của S2 là giải phóng slot cho 25 cand đang pending.
5. 3/7 panel reviewer nêu tác giả không vẽ hộp — đó là bất đồng với
   author, không phải engine miss. Hướng fix: incumbent retention
   (slot monopoly + rewrite drift), không phải generator mới.
