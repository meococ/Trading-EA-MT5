# H0-R — Hybrid Generators With Die Rules (R81 §81.5(4), R82 §82.6)

Estimate only — verdict INFO pending EVAL-AUDIT and a Lead ruling.
Parent = C-3 `1a5502129b4c1554` (uip2_pbbirth@8361fe85, 623 canonical
TUNE windows). Pipeline, scoring loop and parent identical to H0
(`h0_hybrid.py` imported, never forked). Die rules = TT-2 predicates
imported verbatim from `research/perception/trade_tags.py`; a thin
adapter (`h0r_hybrid.py`) feeds the baseline object dict shape into
those predicates and computes the first-set bar incrementally.
**Adapter verification: 25,278 checks, 0 mismatches** — every kill and
every survival decision was re-confirmed by calling the imported TT
predicates at the death bar / last bar.

## 1. M1 rows

| arm | box@1 | level@1 | line@2 | bracket | clutter |
|---|---|---|---|---|---|
| C-3 (parent) | 16/119 | 7/76 | 20/193 | 29/85 | 4.33 |
| H0-a | 16/119 | 16/76 | 20/193 | 29/85 | 6.00 |
| **H0R-a** | 16/119 | **7/76** | 20/193 | 29/85 | **4.50** |
| H0-b | 16/119 | 7/76 | 29/193 | 29/85 | 7.67 |
| **H0R-b** | 16/119 | 7/76 | **29/193** | 29/85 | **7.67** |
| H0R-c *(diagnostic only — see §2)* | 16/119 | 7/76 | 29/193 | 29/85 | 8.00 |

Clutter = published cumulative census (same method as C-3 4.33 and
H0). Die-rule semantics follow the S2 convention: an emitted object
killed by a die rule inside the window before its natural end is "not
drawn, not counted"; naturally-retired objects (the generator's own
break rule) stay counted, like the engine's own DELETED objects.

## 2. Keep rule

| leg | H0R-a | H0R-b |
|---|---|---|
| target family ≥ parent | level 7 ≥ 7 PASS | line 29 ≥ 20 PASS |
| every family ≥ parent−1 | all PASS | all PASS |
| clutter ≤ 5.0 | **4.50 PASS** | **7.67 FAIL** |
| prefix invariance 20 panels | 20/20 PASS | 20/20 PASS |
| **verdict** | **PASSES** (mechanically; zero net gain — see §3) | **FAILS** |

H0R-c: per the ruling it runs only if BOTH a and b pass. H0R-b fails
the clutter leg, so H0R-c is **not an executed arm** — its row above
is diagnostic only (clutter 8.00 would fail anyway).

## 3. Survival of H0's +9

**H0R-a — levels: the +9 is fully erased.**
- H0-a hit 15 goldens that C-3 missed (net +9 after 6 losses). Under
  the die rules **6 of the 15 survive**; the arm lands at 7/76 —
  exactly the parent count (different identity: +6/−6 vs C-3).
- All **9 lost H0-a hits are attributed to `zombie`** (the matching
  pick's price had >2 full-history close side-switches; most die at
  birth). None to stale_far, none to ranking displacement.
- Reading: the Donchian-alt edge lives on prices that are *already
  crossed* historically — precisely the objects the zombie predicate
  retires. The retention rules fix the clutter (6.00→4.50) and, in
  doing so, remove the gain. Generation and retention were the same
  objects.

**H0R-b — lines: the +9 fully survives; clutter is untouched.**
- All **21 gained goldens survive** (29/193 kept, zero hit loss,
  flips vs H0 = none).
- But clutter stays 7.67: only **7 in-window kills** across all 198
  panels (5 stale_far + 2 line_broken). tdlines objects are already
  short-lived — the generator's own qualified-break death and the
  span_max=84 cap retire them long before `stale_far` (3×ABR +
  24-bar touch gap) can bite, and `line_broken` (2 consecutive
  beyond-side closes) almost always loses the race to the
  generator's first-close break (only 4 first-fire wins overall).
- Reading: the td-lines clutter is a **birth-rate / churn problem**
  (~68 re-draws/day), not a retention problem. Die rules cannot fix
  it; the lever would be birth throttling (caps/cooldown), which is
  out of scope here.

## 4. Per-rule kill counts (per panel·object, then in-window subset)

| source | rule | objects killed (all) | killed inside [w0,w1] | H0 hits killed |
|---|---|---|---|---|
| donchian (a) | zombie | 5108 | 2159 | 9 |
| donchian (a) | stale_far | 691 | 169 | 0 |
| tdlines (b) | stale_far | 259 | 5 | 0 |
| tdlines (b) | line_broken | 4 | 2 | 0 |

(An object satisfies its rules at the first bar any sets; killers
record every rule firing at that bar. Counts are per panel·object —
an object spanning several panels counts once per panel it dies in.)

## 5. Flip tables

**H0R-a vs C-3 (level):** +6 gained / −6 lost.
gained: 9.21b, 9.34b, 9.36b, 9.42c, 9.48c, 9.49a.
lost: 9.3c, 9.40c, 9.51b, 9.5c, 9.61c, 9.64c.

**H0R-a vs H0-a (level):** −9 lost (all zombie-killed):
9.1b, 9.24c, 9.3c, 9.40b, 9.51a, 9.54b, 9.57b×2, 9.66a.

**H0R-b vs C-3 (line):** identical to H0-b's map — +21 / −12
(9.11c, 9.24a, 9.27c, 9.29a×2, 9.30a, 9.35b, 9.42c, 9.46b, 9.50b,
9.51a, 9.55a, 9.58b, 9.59a, 9.59b, 9.60a, 9.60b×2, 9.61c, 9.65b,
9.6a gained; 9.17a, 9.18c, 9.1a, 9.1b, 9.22a, 9.23a, 9.2b, 9.44c,
9.48c, 9.4a, 9.60c, 9.65a lost).

**H0R-b vs H0-b:** no flips — identical hits at every golden.

## 6. G-KIT override

`practice/H0R_a_objects.jsonl` — 12 fixed panels, one row each in
HOWTO.md item spelling. Base = verbatim objects of
`review/sets/c3/<panel>.json` minus the level family (LEVEL_CARRIED,
MINI_LEVEL), plus the arm's live donchian objects at the review tau
(die rules + C1@1.0 gate). 10 of 12 panels have **zero** surviving
arm levels at tau — the chart is honest about what the die rules
leave (9.25a +1 level, 9.40a +1 level). No override for b/c (fail /
not run). Reviewer note: line_broken stays a trade-view hide tag;
this file shows the arm chart, not an engine change.

## 7. Limitations

- Census convention for killed objects follows the S2 analogue
  (killed → not counted). If EVAL-AUDIT instead counts rule-killed
  objects like engine DELETED, H0R-a clutter reads 6.00 (FAIL) and
  nothing passes — this convention is the single point the audit
  must confirm.
- Zombie uses full-history switches (TT predicate verbatim). A
  since-birth zombie variant would keep more levels — that would be
  tuning; not tried.
- Kill counts are per panel·object, not per unique object.
- line_broken marginal effect is structurally ~0 on tdlines because
  the generator already self-kills on a weaker single-close break.

## E5 — Tóm tắt cho anh

- Em gắn "luật chết" (stale_far, line_broken, zombie) vào các object
  do máy sinh, rồi đo lại nguyên hàng M1.
- Arm a (levels): clutter giảm 6.00 → 4.50 — nhưng luật zombie giết
  luôn cả +9 hit mới kiếm được; level về đúng 7/76 như C-3. Chính
  những level "đắt" nhất lại nằm ở giá đã bị cắt qua nhiều lần.
- Arm b (lines): giữ nguyên 29/193 (+9 hit còn sống hết) — nhưng
  clutter vẫn 7.67, vì tdlines chết tự nhiên quá nhanh, die rules
  không kịp tác dụng; rác ở đây do sinh nhiều chứ không phải sống lâu.
- Kết luận: die rules chữa đúng bệnh "giữ object quá lâu" — nhưng đó
  chỉ là bệnh của levels. Lines cần "luật sinh ít lại" (throttle),
  không phải luật chết. G-KIT override cho arm a đã ghi ra
  `practice/H0R_a_objects.jsonl`.
