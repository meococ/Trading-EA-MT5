# AD-EST — "adopt, don't yield" + UIP rewrite anatomy (Ruling 86)

Base: C-3 @e7d13384 (`fa2e52e5` + TT-3), canonical caches
`run_uip2_pbbirth@8361fe85`, tau-keyed runs (same loader as YS_EST).
Tags imported verbatim from `trade_tags.py` (`s_stale_far`,
`s_box_broken`, `tol_e`).  Script: `boxlab/ad_est.py` →
`boxlab/ad_est.jsonl` (88 rows).  Read-only; numbers only.

## PART 1 — diagnostic

### 1a. box@1 at golden τ — age anatomy (119 decisions)

| group | metric | n | med | p25 | p75 |
|---|---|---|---|---|---|
| hits (16) | identity age (`j_tau − t_birth`) | 16 | **98** | 83 | 112 |
| hits | band-version age (`j_tau − last write`) | 16 | **2** | 1 | 2 |
| hits | drawn width (`j_tau − version t0`) | 16 | **24** | 16 | 35 |
| misses (103) | identity age | 103 | **129** | 98 | 158 |
| misses | band-version age | 103 | **3** | 1 | 10 |
| misses | drawn width | 103 | **30** | 19 | 48 |

Author's box length: median **17** bars (DR-RULES).  Corrections to
the withdrawn R85 §85.2(d) claim: the incumbent's *identity* is indeed
~6–8× older than the author's box (98–129 vs 17 bars), but its
*current band version* is young (median 2–3 bars) and its *drawn
width* (24–30) is in the author's range (p25 16–19 vs 17).  The UIP
object rewrites constantly; "old object" ≠ "old band".

### 1b. Did the incumbent rewrite inside the candidate's window?

46 E3 rows carry an edge-matched candidate.  The incumbent's
`uip_rewrite` events (object events) inside the candidate's
pool-alive window:

| outcome | rows | detail |
|---|---|---|
| rewrote inside window | **24** | 54 writes total; written band vs cand edges: hi-edge med **0.45 ABR** (p75 0.81), lo-edge med **0.95 ABR** (p75 2.81) — writes land *near* the pending band but rarely on it |
| no rewrite | **22** | clause table below |

Clause blocking per no-rewrite row (replay of `pipes.py:66-141` at
each confirmed pivot `t_conf` inside the window):

| clause | rows | meaning (file:line) |
|---|---|---|
| `no_confirmed_pivot` | 9 | no new pivot confirmed in window — trigger never evaluated (`pipes.py:50` event_step only fires on pivots) |
| `no_cand` | 12 | pivot fired but neither rd pair (`idx−prev.t_ext ≥ 8` AND `\|Δprice\| ≤ 2.0p`, `pipes.py:76-91`) nor pb (`idx−t0a ≥ PBSEP`, `pipes.py:92-107`) formed a cand |
| `pb_only` | 1 | only `ev_pullback_end` formed → `uip_skip_pb`, pb cannot rewrite under C-3 (`pipes.py:122-124,137-140`) |

Root read: in half the rows the incumbent *does* hear and write —
but each write adopts the **new event cand's own geometry**
(`pipes.py:113,125-136`), which drifts off the pending cand's band
(hi-edge ~0.5 ABR, lo-edge ~1–3 ABR).  The rewrite mechanism never
consults the pool: the pending edge-matched cand cannot influence the
written band.  In the other half the trigger is starved (no pivots)
or gated (pair/pb clauses).

## PART 2 — STEP 0: is "rewrite to an external cand's band" expressible?

**Mechanically yes.**  Adoption = one more `uip_rewrite` write:
the same code path (`pipes.py:125-136`) sets
`geometry["top"/"bottom"/"t0"]` and logs `uip_rewrite`.  A build
needs: (1) a flag (e.g. `ev_uip_adopt`, default OFF ≡ parent); (2) a
hook — the natural point is `_grant_pass` where box cands are denied
by the famlive slot (`salience.py:800-824` `fam_n >= famlive_box`),
i.e., where `outranked`/`suppressed_budget`/`fam_capped` outcomes are
decided — call the write instead of logging the outcome.  Trigger
needs `close[j]` + pool cands + incumbent band — all available there.

**Carried levels:** unchanged.  Adoption keeps `o.id`; levels spawned
with `src=o.id` (`boxes.py:1211-1223`) keep their parent — no cascade.
(And in the measured corpus no live `LEVEL_CARRIED` uses
`broken_box_edge_*`/`congestion_edge` routes anyway — the channel is
present in code, empty in data.)

**Caps/budgets:** untouched.  Adoption is a geometry write, not a
birth — no `signal`/`context`/`budget_hard` consumption, no
`famlive` change; under `ev_uip_lvfree` the incumbent keeps costing
only the famlive slot.

**One semantic deviation to flag:** the ruling's `t_left = c.t_left`
is stronger than real `uip_rewrite` (which sets only `geometry["t0"]`,
leaving `o.t_left` fixed — TT-3's break anchor `j0 = ob.t_left`,
`engine.py:645-651`).  The sim follows the ruling: adopted versions
re-anchor `j_from = c.t0` and TT-3 facts re-derive per version; real
versions keep `j_from = ob.t_left`.

## PART 2 — results

### 1. Box hits (V2.match on the simulated box@1 band at τ)

| variant | hits lost | hits gained | net |
|---|---|---|---|
| AD-a | **1** (9.7b@540 BOX0001, 2 adoptions) | 2 (9.16c@1070, 9.23c@985) | +1 |
| AD-b | **1** (9.7b@540 BOX0001, 2 adoptions) | **4** (9.4b@855, 9.16c@1070, 9.45b@740, 9.56c@840) | **+3** |

The shared loss: on 9.7b the incumbent's band was already
golden-correct ([13224.3,13236.5] ⊂ golden [13222,13239]); while price
roamed outside it, a pending cand containing `close[j]` qualified →
two adoptions walked the band off the golden.  AD-b's extra gate
(broken + post-exit cand) made adoptions more selective: fewer
adoptions, more gains.

### 2. Churn (adoptions per panel, 119 box-golden panels)

| variant | med | p90 | max | hit panels (16) |
|---|---|---|---|---|
| AD-a | **5** | 9 | 16 | med ~3.5, up to 9 |
| AD-b | **4** | 7 | 11 | med ~3, up to 7 |

### 3. Cross-family at-risk (level 7, line 20, bracket 29 hits)

| family | AD-a | AD-b | reason |
|---|---|---|---|
| level | **0** | **0** | adoption keeps id+src; no live carry levels seeded from box edges in corpus |
| line | **0** | **0** | no birth → no cap/budget touched (STEP 0) |
| bracket | **0** | **0** | same |

Arm-Y leg (gross level−4, line−3, bracket−0 from
`y_measure_y1.jsonl`): AD fires on **all 7** lost-hit panels before τ
(AD-a 4–12, AD-b 2–10 adoptions each) — activity is present but no
at-risk channel exists per STEP 0.

### 4. Twelve fixed review panels

| panel | AD-a adoptions | AD-b | box@1 author-match (a/b) |
|---|---|---|---|
| 9.2b | 8 | 5 | no / no |
| 9.10c | 8 | 6 | no / no |
| 9.11b | 6 | 6 | no / no |
| 9.17b | 4 | 5 | no / no |
| 9.25a | 2 | 2 | no / no |
| 9.33c | 6 | 6 | no / no |
| 9.36c | 9 | 7 | no / no |
| 9.40a | 4 | 3 | no / no |
| 9.42b | 5 | 4 | no / no |
| 9.48b | 9 | 4 | no / no |
| 9.52a | 2 | 2 | no / no |
| 9.57b | 6 | 4 | no / no |

Adoptions happen everywhere but **no panel ends with author
geometry** — the same wall as §86.2: the adopted band is a live pool
cand, and pool cands still carry the wrong geometry (the E3
edge-matched cand is consumed only when it happens to be top-scored
AND its band contains close — rarely the authored one).

## 5. Gate table (Lead's fixed rule)

| gate | AD-a | AD-b |
|---|---|---|
| box hits lost = 0 | **FAIL (1)** | **FAIL (1)** |
| hits gained ≥ 3 | FAIL (2) | **PASS (4)** |
| at-risk ≤ 1 per family | **PASS (0/0/0)** | **PASS (0/0/0)** |
| median adoptions ≤ 3 | **FAIL (5)** | **FAIL (4)** |

## Tóm tắt (4 dòng)

- PART 1: incumbent identity già (med 98–129b) nhưng band version rất
  trẻ (med 2–3b), drawn width 24–30 ≈ author's 17 — R85's "119 vs 17"
  claim đã đúng sau khi đo lại đúng quantity.
- PART 1b: 24/46 edge-matched rows incumbent CÓ rewrite trong window
  nhưng viết geometry của event-cand mới (lệch cand ~0.5–1 ABR), 22
  rows bị starve (9 no-pivot, 12 pair-gates, 1 pb-only).
- AD-a: mất 1 hit (9.7b — adopt kéo band đúng đi khi giá roaming),
  +2 gained, churn med 5 → FAIL 3/4 điều kiện.
- AD-b: mất cùng 1 hit, **+4 gained** (PASS), at-risk 0/0/0, churn
  med 4 → FAIL hits-lost + churn; expressive được qua uip_rewrite +
  flag mới, nhưng chưa đủ gate.
