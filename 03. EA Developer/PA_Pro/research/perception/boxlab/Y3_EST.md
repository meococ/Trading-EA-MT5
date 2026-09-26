# Y3 EST — yield on stale_far ALONE (R84 §84.5)

BOX-LAB, read-only, 23/09 ~15:00Z. Parent C-3 @e7d13384 (trade_tags=1
facts). Caches `run_uip2_pbbirth_8361fe85*` are canonical-identical
(TT-3 verified ON ≡ OFF ≡ parent 623/623 — geometry unchanged; tag
predicates re-derived per object per bar via `trade_tags.py`
imports, never re-implemented). Script `boxlab/y3_est.py`; rows
`boxlab/y3_est.jsonl` (102 rows).

**Method notes (stated before numbers):**
- Per golden decision the tau-keyed engine run is loaded
  (`run_*_{date}_{tau}.pkl`, same file the official M1 loads — a run
  stopped at tau). Reproduces the official row: **box 16/119**.
- `stale_far` = `trade_tags.s_stale_far` verbatim: dist(close→band)
  > 3·ABR20 **and** last band touch > 24 bars before t. Evaluated per
  bar (the engine writes facts per bar, no latching — `engine.py:700`).
- The incumbent is the box1 object at tau from `e3_diag.jsonl`
  (verified live at the kill bar in all 59 rows). Its band at any bar
  is reconstructed from `uip_birth`/`uip_rewrite` write events (UIP
  objects rewrite; other box objects are static).
- "Frees" = incumbent's **first stale-onset bar ≤ the cand's pending
  end** (its last pool event, or tau for `proposed`-pending). Upper
  bound: the freed slot promotes the pool's best cand at that bar,
  not necessarily ours — a build measures that.

## Item 1 — the 16 C-3 box hits at their tau

| measure | count |
|---|---|
| box hits (official check: 16/119 reproduced) | 16 |
| carrying `stale_far` at tau | **0** |
| ever had a stale onset in [birth, tau] | **0** |

→ **Y3 loses 0 hits.** (Hits sit at price by construction —
`stale_far` needs >3·ABR distance plus a 24-bar no-touch gap.)

## Item 2 — incumbents of the 59 BUDGET_CUT misses

| measure | count |
|---|---|
| incumbent `stale_far` at the cand's kill bar | **5** |
| incumbent `stale_far` at tau | **5** (same set) |
| stale onset while the cand still pending | **20 rows** (17 unique incumbents) |
| of those: an edge-matched cand existed | **11 rows** (10 unique incumbents) |

Stale@kill incumbents: 9.17b BOX0001 (×2 goldens), 9.17c BOX0001,
9.23c BOX0001, 9.45b BOX0006.

Edge-matched frees (upper bound): 9.17b@730, 9.16c@1070, 9.17b@705,
9.17c@830, 9.23c@985, 9.24a@720, 9.24b@820, 9.25b@775, 9.45b@740,
9.48b@705, 9.59c@1035.

## Item 3 — the 7 named review panels

| panel | incumbent stale_far | frees edge-matched cand |
|---|---|---|
| 9.10c / 9.11b / 9.25a | — (no current author box) | — |
| 9.17b | **yes** (onset bar 121; cand died at 137) | **yes** |
| 9.2b | no | no |
| 9.33c | no | no |
| 9.52a | no | no |

Note: the headline panels 9.33c/9.2b/9.52a are NOT rescued — their
incumbents sit near price with the wrong geometry; `stale_far`
requires distance, which they never had.

## Item 4 — context (Gemini's lifespan ask + retest warning)

- **box@1 age at tau:** median **119 bars** (~10h on M5), p25 95,
  p75 154, max 217 (n=119). Lifespan of the same objects: median
  **271 bars** — picks are old; they persist for the whole panel.
- **Retest check:** of 23 unique box1 incumbents that are
  `box_broken` at tau, **21 (91%) are revisited by price at the old
  band within 24 bars of `exit_bar`** — the reviewer's warning is
  confirmed in the data (exceptions: 9.42b, 9.56a-shock).

## Numbers for the Lead's decision rule

Rule stated in the order: build only if **0 hits lost** and
**≥5 edge-matched candidates freed**.

| gate | value |
|---|---|
| hits lost | **0** |
| edge-matched candidates freed (upper bound) | **11 rows / 10 unique incumbents** |

Numbers only — the decision is the Lead's. Caveats carried: "freed"
is the moment the incumbent first goes stale while the cand is
alive; which cand the pool then promotes is engine behaviour a build
measures (arm Y promoted only 5 of ~50 freed slots).

## Tóm tắt (4 dòng)

1. Y3 (giết incumbent khi `stale_far`) mất **0/16 hit** — không hit
   nào từng stale (hit nằm sát giá theo định nghĩa).
2. Trong 59 incumbent chặn slot: 5 stale ngay tại kill-bar, 20 stale
   khi cand còn sống → giải phóng tối đa 20 slot, trong đó **11 có
   cand đúng-edge** (10 incumbent duy nhất) — vượt bar ≥5 của Lead.
3. Named panels: chỉ 9.17b được cứu; 9.33c/9.2b/9.52a incumbent sát
   giá sai-geometry, không stale → Y3 không chạm tới ca chính.
4. Context: box@1 già median 119 bars; 91% incumbent box_broken bị
   giá retest trong 24 bars — cảnh báo của reviewer đúng; "freed" là
   upper bound, ai lên slot do pool quyết, build mới đo được.
