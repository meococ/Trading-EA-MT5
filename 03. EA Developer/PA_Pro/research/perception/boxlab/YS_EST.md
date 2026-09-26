# YS-EST — "yield without death" offline estimate (Ruling 85)

Base: STABLE C-3 @e7d13384 (`fa2e52e5` + TT-3 facts), canonical caches
`run_uip2_pbbirth@8361fe85` (canonical-identical, 623/623 verified),
tau-keyed runs stopped at each golden-decision τ (same loader as
Y3_EST).  Tags imported verbatim from `trade_tags.py`
(`s_stale_far`, `s_box_broken`, `tol_e`) — never re-derived.
Script: `boxlab/ys_est.py` → `boxlab/ys_est.jsonl` (190 rows).
Read-only.  Numbers only — the build decision is the Lead's.

## STEP 0 — how the box slot and budgets work in C-3

**Slot.**  A box incumbent occupies the `famlive_box=1` family slot:
`fam_n` counts ACTIVE objects of the box family (`salience.py:820-824`
`self._fam(o.type)=="box"`, ro_skip off since `fam_context/box_prio/
ctx_yield` are all False → `RANGE_OPEN` counts too).  Grant blocks a
new box-family birth while `fam_n >= 1` (`salience.py:824`).

**Budget the incumbent occupies.**  Under `ev_uip_lvfree=True` the
persistent UIP object (`meta_uip_persist`) is excluded from the class
live-count AND from `n_act` (`salience.py:789-798`: "box ink only —
never occupies a shared or joint slot, never a displacement victim"),
so the UIP incumbent holds only the famlive slot.  A non-UIP box
(`BOX`) additionally occupies the `signal` class budget
(`budget_signal=3`), `budget_hard=9`; `RANGE_OPEN`/`CONTEXT_RANGE`
occupy `context` (`budget_context=2`).  Dead/broke objects reclass to
`context` (`salience.py:783-795`).

**Sharing with level/line/bracket.**  Each family has its own
`famlive` (level 1, line 2, bracket 1) — the box slot is NOT shared
with them.  What IS shared: `BOX`, `LEVEL_CARRIED`, `MINI_LEVEL`,
`PATTERN_LINE`, `BRACKET` are all `signal` class
(`kernel.py:9`, `SIGNAL`) → a +1 box successor consumes one of 3
signal slots that level/line/bracket births also need, plus one of 9
hard slots (`budget_hard`).  `CONTEXT_LINE` is `context` class —
unaffected.  `joint_struct=0` in C-3 (`salience.py:436,1511` off).

**Derivation.**  YES — a box's edges DO parent levels: on
`break_confirm` the box spawns `broken_box_edge_<side>` at the broken
edge and `congestion_edge` at the opposite edge, both `src=o.id`
(`boxes.py:1211-1223`).  Lines/brackets are not derived from boxes.
So a *closed* box stops seeding carry levels; a *yielded-but-live*
box keeps seeding them (break_confirm can still fire on it).

**Is "demote without close" expressible?**  **NO.**  The architecture
has no "ACTIVE but never rank-1 again" state:
- `ctx_yield` (`salience.py:604-654`, flag OFF in C-3) is
  DELETED-then-restore, context objects only — removal, not demotion.
- `lvfree` exclusion (`salience.py:789-798`) makes an object
  budget-free but it still HOLDS rank-1 (it is the incumbent) —
  the opposite direction.
- `dead`/`broke` geometry flags reclass the budget to context but the
  object keeps its famlive slot and rank eligibility.
A real YS build needs a new `yielded` flag read by `_grant_pass`/
ranking.  The estimate below therefore simulates the *specified*
demote semantics directly on the slot-holder chain (incumbent stays
ACTIVE with its facts, never re-holds the slot, counted lvfree-style
— i.e., excluded from class/hard counts after yield, the nearest
existing precedent); where the close-version differs it is flagged
`"close"` in §5.

**Model.**  `simulate()`: bar-by-bar to τ; holder(j) = ev_-why object
if active else max-score active box object (famlive=1 ⇒ one holder);
YS-a yield = first `s_stale_far` onset on the holder's *current* band
version (band history rebuilt from `uip_birth`/`uip_rewrite` events);
YS-b yield = first bar where `s_box_broken` is true on the current
band version (j_from = `o.t_left`, engine semantics — `object_stats`
uses `min(ob.t_left, j1)`) AND a pool cand born strictly after
`exit_bar` is alive (`cand_log` per-bar entries, terminal-outcome
aware) AND its birth passes the signal/hard caps (lvfree-aware).
Yield is sticky; the successor becomes holder at the yield bar
(virtual holder, same yield rules apply → path dependence preserved).

## 1 — Box hits (16): lost per variant

| variant | direct loss | path loss | total lost |
|---|---|---|---|
| YS-a | 0 | 0 | **0/16** |
| YS-b | 16 | 0 extra | **16/16** |

YS-a: no hit object ever reaches `stale_far` before its τ, and no
yield event lands on a hit panel (33 YS-a yield events corpus-wide,
all on non-hit panels except where noted below).

YS-b: every hit object itself yields before τ (all `direct`).  Root
cause is the TT-3 entry-anchored break semantics: the freshly-written
UIP band is thin (≈9–20 pips) and `s_box_broken` fires a run3 break
within a few bars of the write (born-broken ≈59% corpus-wide, per
EVAL-AUDIT 14:49Z).  With ≥1 post-`exit_bar` cand nearly always
pending, the yield fires almost immediately; the successor's thin
band breaks in turn → succession chains (median 5–11 yields/hit
panel, 408 events on measured rows).  Verified by hand on 9.13a:
band [13171.3,13180.6] written bar 9, run3-broken exit_bar 16,
post-exit cand pending bar 20 → yield @20.
List (panel, τ, hit object, first-yield bar):
9.6a@600 BOX0001@33 · 9.7b@540 BOX0001@22 · 9.11a@660 BOX0001@9 ·
9.13a@505 BOX0001@20 · 9.15b@900 BOX0001@41 · 9.17a@475 BOX0001@21 ·
9.18a@515 BOX0001@33 · 9.27a@600 BOX0002@41 · 9.32a@478 BOX0002@33 ·
9.32a@510 BOX0002@33 · 9.34a@495 BOX0004@17 · 9.41b@835 BOX0001@21 ·
9.44b@730 BOX0006@44 · 9.45a@350 BOX0006@36 · 9.58a@545 BOX0001@20 ·
9.61b@895 BOX0001@23.

## 2 — Freed E3 BUDGET_CUT rows (59)

| variant | rows freed | edge-matched freed | unique incumbents | cand was top successor |
|---|---|---|---|---|
| YS-a | 1 | **0** | 0 | 0 |
| YS-b | 2 | **1** | 1 | 0 |

- YS-a frees 9.62b@840 (BOX0003 stale @126; CON0006 — the next real
  holder — also stale @127).  Not edge-matched.
- YS-b frees 9.48a@420 (BOX0001 @37; edge-matched, but the matched
  cand is NOT the top-scored successor — an outranked-by-score
  situation consistent with E3) and 9.53a@250 (not edge-matched).
- Why so far below Y3's "20 rows / 11 edge-matched": Y3 counted each
  incumbent's stale-onset *independently* per row.  Under a sticky
  yield the incumbent yields **once** — its first onset lands inside
  at most one row's pending window (and the successor that takes over
  is young/near-price → rarely goes stale again).  Same for YS-b:
  one succession event per incumbent per window.

## 3 — Cross-family at-risk (level 7, line 20, bracket 29 hits)

A hit is at-risk if a yield event before its τ (a) touches it via the
yielding box's edge/parent (`level-at-yielding-edge`), or (b) its
successor birth fills `signal` cap 3 / `budget_hard` 9 and the hit
object was born after the yield bar (`signal_cap3`/`budget_hard9`).

| family | YS-a | YS-b | one-line reason |
|---|---|---|---|
| level | **0** | **6** | no derivation loss under demote (yielded box keeps seeding carries); YS-b churn keeps the signal cap saturated |
| line | **1** (9.22a PAT0013, signal_cap3) | **17** | same — every successor birth eats a shared signal slot |
| bracket | **1** (9.24c BRA0019, signal_cap3) | **15** | same |

Arm-Y leg (gross losses from `boxlab/y_measure_y1.jsonl` flips,
confirmed by EVAL-AUDIT 14:49Z: level −4, line −3, bracket −0):
level lost 9.5c@1030 LEV0016, 9.32b@571 LEV0013, 9.40c@921 LEV0016,
9.64c@1020 LEV0017; line lost 9.1b@710 PAT0014, 9.44c@1050 PAT0017,
9.60c@1140 PAT0018; bracket lost none.
Yield events on those panels before τ — **YS-a: 0/7 panels**, **YS-b:
7/7 panels** (4–12 events each).  Under YS-b every panel where arm Y
lost a cross-family hit shows heavy yield activity before τ.

## 4 — Twelve fixed review panels

| panel | YS-a yields | YS-b yields | suc edge-matched (b) | suc author-geom (b) |
|---|---|---|---|---|
| 9.2b | 0 | 9 | no | no |
| 9.10c | 0 | 9 | no | no |
| 9.11b | 0 | 7 | no | no |
| 9.17b | 1 (BOX0001 @121) | 6 | no | no |
| 9.25a | 0 | 3 | no | no |
| 9.33c | 0 | 6 | **yes** | no |
| 9.36c | 0 | 10 | no | no |
| 9.40a | 0 | 5 | no | no |
| 9.42b | 0 | 2 | no | no |
| 9.48b | 1 (BOX0001 @117) | 5 | **yes** | no |
| 9.52a | 0 | 3 | no | no |
| 9.57b | 0 | 11 | no | no |

On 9.33c and 9.48b the churn chain does rotate an edge-matched cand
into the slot — but never an author-geometry (ruler `V2.match`) box,
and on 9.33c the match arrives at bar ~203 vs τ ~205 — borderline.

## 5 — Gate table (Lead's fixed rule)

| gate | YS-a | YS-b |
|---|---|---|
| box hits lost = 0 | **PASS (0)** | **FAIL (16)** |
| edge-matched freed ≥ 5 | **FAIL (0)** | **FAIL (1)** |
| at-risk ≤ 1 per family | **PASS (0/1/1)** | **FAIL (6/17/15)** |

**"close" proxy note.**  Under a close-version (incumbent dies at the
yield bar instead of staying live): items 1–2 are identical (the slot
chain is the same — the incumbent never re-holds either way), item 3
strictly worsens because the dead box stops seeding
`broken_box_edge_*`/`congestion_edge` levels (`boxes.py:1211-1223`),
converting the `level-at-yielding-edge` flags into real carry losses.

## Tóm tắt (4 dòng)

- YS-a (stale-only): mất **0/16** hit, nhưng chỉ giải phóng **1 row /
  0 edge-matched** — sticky yield chỉ bắn một lần mỗi incumbent nên
  con số Y3 (20/11) sụp còn 1; at-risk 0/1/1 → trượt gate ở frees.
- YS-b (succession): thoái vị **16/16** hit object — band UIP mỏng
  bị run3-break ngay sau write (born-broken ~59%) và hầu như luôn có
  cand sau `exit_bar` → chuỗi succession liên tục, at-risk 6/17/15.
- "Demote without close" **không expressible** trong C-3 (ctx_yield
  = DELETED+restore context-only; lvfree giữ rank-1) — cần flag mới;
  bản "close" cho số giống hệt ở item 1–2 và tệ hơn ở item 3.
- Gate của Lead: cả hai variant đều FAIL — YS-a trượt ở frees (0<5),
  YS-b trượt cả ba điều kiện; không build, chỉ report.
