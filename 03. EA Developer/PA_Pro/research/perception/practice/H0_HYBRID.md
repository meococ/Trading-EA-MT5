# H0 — hybrid objective generators inside the full C-3 chart

Ruling 78 §78.4(1), lane pa-atlas, run 2026-09-23 09:24Z via
`heavy_run.py --lane pa-atlas`.  Cache-only estimate — no engine run,
no flag, no build.  Script: `practice/baselines/h0_hybrid.py`;
per-event rows: `h0_{a,b,c}.jsonl`; aggregates: `h0_summary.json`.

**Question:** if the objective generators (bl_donchian_alt |C1@1.0|,
bl_tdlines_k2 |C7@2|) REPLACE the engine's level/line picks inside
the full chart, what is the complete M1 row?

## Setup

- Parent: C-3 = STABLE `uip2_pbbirth@8361fe85e73f9437`, the 623
  canonical tau-clipped caches (R75 §75.6).  Brackets/marks stay
  C-3's.  Engine-side picks via `snapshot.live_records` +
  `recall_at_k.rank_live` (the replay path, not a new selector).
- Baseline-side picks: live-at-tau objects → `bl_common._rec` →
  DR-RULES gate features on **engine** EMA25/ABR20/pivots
  (`DR_RULES_baselines.feats`, imported) → keep → rank → top-k.
- Events: canonical set (golden scorable taus + mark taus + w1):
  **625 windows, 0 pickle misses.**
- Clutter: **published cumulative window census** — per panel
  (all objects intersecting [w0,w1] + marks) / scorable goldens,
  median.  Same method as the C-3 row's 4.33.
- Substitution semantics: the baseline generator owns the family's
  budget slots; the other slots stay C-3's.  First-order estimate —
  no cross-family coupling is modelled (the engine's own structure
  competition is not replayed; R75 §75.2a caveat applies).

## M1 rows

| arm | box@1 | level@1 | line@2 | bracket | clutter (census) |
|-----|-------|---------|--------|---------|------------------|
| C-3 (parent, reproduced) | 16/119 | 7/76 | 20/193 | 29/85 | **4.33** |
| H0-a (donchian\|C1@1.0 levels) | 16/119 | **16/76** | 20/193 | 29/85 | 6.00 |
| H0-b (tdlines k2\|C7@2 lines) | 16/119 | 7/76 | **29/193** | 29/85 | 7.67 |
| H0-c (both) | 16/119 | **16/76** | **29/193** | 29/85 | 10.00 |

Parent reproduction is exact (16/7/20/29 + 4.33) — the pipeline is
faithful.  `squeeze`/`annot` goldens: 0/2, 0/4 in all rows (unchanged,
not part of M1).

## Keep rule (R78 §78.4, fixed)

| leg | H0-a | H0-b | H0-c |
|-----|------|------|------|
| target-family hits ≥ parent | PASS (16 ≥ 7) | PASS (29 ≥ 20) | PASS (both) |
| every family ≥ parent−1 | PASS (0 moved) | PASS (0 moved) | PASS (0 moved) |
| total clutter ≤ 5.0 | **FAIL (6.00)** | **FAIL (7.67)** | **FAIL (10.00)** |
| prefix invariance, 20 rnd panels/source (seed 78) | PASS 20/20 donchian | PASS 20/20 tdlines | PASS 20/20 both |

**All three arms fail the keep rule on the clutter leg.**  The hit
gains are real and the causality is clean; the published census —
which counts every object that ever appears in the window, not just
what is picked — is what kills them.  C-3's own level share of the
census is ~0.2 objects/panel; donchian|C1 contributes ~1.9.  TD
lines redraw ~3.4 extra objects/panel over C-3's line share.

## M2-facing diagnostics (pass-rate on the arm's picked objects)

| rule | family | C-3 objects | substituted objects |
|------|--------|-------------|---------------------|
| C1@1.0 | box | .928 (580/625) | — (boxes stay C-3) |
| C3w@3.0 | box | .794 (496/625) | — |
| C4w@4 | box | .880 (550/625) | — |
| C6g@2.0* | box | .016 (10/625) | — |
| C7f@2 | level | .273 (163/597) | donchian\|C1: .261 (146/560) |
| C8a@1 | level | .275 (164/597) | donchian\|C1: **.996** (558/560) |
| C7f@2 | line | .681 (773/1135) | tdlines\|C7: **.802** (550/686) |

*C6g needs a golden ruler tolerance (`tol_g`); engine/baseline
objects have none — reported at the fixed meas-precision proxy
2.0 pips (golden box tol_px ∈ {1.5, 2.0, 5.0}).

Read: the substituted objects are **Owner-cleaner** than C-3's on the
rules that fit them — donchian levels almost never sit behind a newer
extreme (C8a .996 vs .275), TD lines cross already-woven price less
often (C7f .802 vs .681).  The C-3 boxes are untouched and keep their
weaknesses (C6g .016 — lone edges everywhere).

## Per-panel flips vs C-3 (hits gained / lost)

| arm | family | gained | lost | net | panels touched |
|-----|--------|--------|------|-----|----------------|
| H0-a | level | 15 | 6 | +9 | 19 |
| H0-b | line | 21 | 12 | +9 | 31 |
| H0-c | level | 15 | 6 | +9 | 19 |
| H0-c | line | 21 | 12 | +9 | 31 |

No cross-family flips by construction (substitution is per-family).
Flip detail per panel: `h0_summary.json → arms.*.flips`.

## Limitations

- **First-order estimate.**  In the real engine, freeing/changing
  picks can alter other families through structure competition and
  the shared budget (R75 §75.2a measured exactly that).  These rows
  bound the upside, not the transfer.
- **Clutter is the binding constraint.**  The generators emit every
  qualifying object; C-3 emits few.  A passing variant needs a
  *retention* story (die-earlier, dedupe, or budgeted visibility),
  not a better filter — C1@1.0 already removes 68% of live donchian
  picks and still leaves census +1.7.
- The census counts objects *intersecting* the window regardless of
  picks; a "shown set" smaller than the emitted set would score
  better — but that is exactly the engine's own salience layer, which
  this estimate bypasses.
- C6g on non-golden objects uses the 2.0-pip proxy (golden tol_px
  varies 1.5–5.0); M2-facing only, no M1 impact.
- Prefix-invariance sample: 20 random panels, seed 78, per source —
  both sources pass 20/20 (keys: type, birth, birth_drawn, geometry;
  die ignored as unknowable-at-tau, same convention as EVAL-AUDIT).

## Tóm tắt cho anh (6 dòng)

1. Gắn máy sinh level Donchian (lọc EMA gần) vào chỗ level của C-3: level@1 từ 7 lên **16/76** (+9), không mất hit nào khác.
2. Gắn máy sinh TD-lines (lọc zombie) vào chỗ line: line@2 từ 20 lên **29/193** (+9), không mất hit nào khác.
3. Gắn cả hai (H0-c): level 16 + line 29, box 16 và bracket 29 giữ nguyên — bản đồ tốt nhất từ trước tới giờ.
4. Nhưng cả ba arm đều **trượt keep-rule ở chân clutter**: 6.00 / 7.67 / 10.00 so với trần 5.0 — máy sinh vẽ nhiều object hơn engine giữ lại.
5. Object máy sinh **sạch hơn** theo luật của anh: level gần như không bị extreme mới lấn (C8a 99.6%), line ít cắt giá đã dệt (80%).
6. Kết luận: thế hệ object đã thắng; thứ chưa thắng là **kinh tế giữ lại** — cần cơ chế retire/dedupe trước khi đề xuất build.
