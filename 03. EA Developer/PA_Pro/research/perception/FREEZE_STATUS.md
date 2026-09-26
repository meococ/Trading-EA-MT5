# FREEZE_STATUS — PA-PRO perception engine (P-FREEZE, 23/09)

## Frozen build

- **STABLE C-3:** `1a5502129b4c1554` — verified by EVAL-AUDIT 04:29Z
  (198/198 byte-identical, suite 72/72; `evalcheck/GATE_PACK_C3_1a550212.md`).
- Lineage: C-2 `4c2df34d7a2a8ee3` (K1–K9 + F1) + UIP-rd event box
  (`uip2_lvfree_pbbirth` folded into defaults).
- Snapshot: `_scratch/freeze_candidates/1a5502129b4c1554/` + SHA256.txt.
- Working tree (post-C-3 migration, byte-identical behaviour):
  `bbdee030512d7cfa` — Phase A (kernel.py / objects.py / pipes.py;
  `salience.round()` split into named stages; `Candidate.fam` shadow
  tag; A6 family-order retire REVERTED per ARCH_REVIEW (c) BLOCK)
  plus B1 (`Salience.pool_view` per-family read-time views behind
  `arch_v2`, verified by EVAL-AUDIT 08:13Z) and B5 (EventBox
  `_ev_uip_step` relocated verbatim to `BoxPipe.event_step`,
  verified by EVAL-AUDIT 08:42Z).  Canonical 623/623 + suite 72/72
  at every landing; R-1 pool-occupancy probe aboard (observational
  only: pool peak median 34 / max 53, box 30 / line 14 / level 13 /
  bracket 12).
- File set (`funnel.V1_FILES`): boxes.py, cet.py, engine.py, gates.py,
  kernel.py, levels.py, lines.py, objects.py, params_v1_1.json,
  patterns.py, pipes.py, salience.py, swings.py.
- Flags ON (defaults): the C-2 list plus `salience.ev_uip`,
  `ev_uip_persist`, `ev_uip_lvfree`, `ev_uip_pb_birth`
  (one persistent update-in-place event box per panel; rd rewrites
  move edges; pullback_end may birth it at the v0 route gate; the
  object is excluded from level seeding and shared caps).

## M1 (canonical `_m1.py`, ruler eval_v2 `50e11fd5`, TUNE 198)

| family | C-3 | v0 | verdict |
|---|---|---|---|
| box@1 | .134 (16/119) | .134 | **met — v0 parity** |
| level@1 | .092 (7/76) | .066 | met (point estimate) |
| line@2 | .104 (20/193) | .093 | met (point estimate) |
| bracket@1 | .341 (29/85) | .388 | reported, outside M1 |
| clutter med | 4.33; 110/179 panels ≤5.0 | ≤5.0 | met |

Suite: **72/72** on the unmodified suite of record
(`research/perception/tests/`).

Throughput (R71 §71.3): median 212 bars/s over 55 DESIGN days,
day-54 107 b/s — no F1 regression (F1 baseline day-54 ~104 b/s).

## Known limits (Owner-facing)

1. **Box hit count = v0 parity, precision thin.** C-3 reaches
   box@1 .134 = v0, but precision is 0.041 (many engine boxes, few
   hits) and CIs overlap v0 on every family — M1 is met on point
   estimates only. The Owner's M2 blind-precision check is the real
   test of whether the drawings look right.
2. **Fixture conflict — resolved on C-3.** The suite is 72/72:
   `test_pullback_end_box_birth` cured by `ev_uip_pb_birth`
   (pullback_end may birth the UIP object at the v0 route gate).
   The older conversion-in-place conflict stays documented in
   FIXTURE_CONFLICT.md.
3. **Ink ~3–4× the author's** (clutter median 4.33 vs golden 1.0).
4. **Drawing follows the calendar**, not the text narrative (SCALE C-1).
5. **Level residual.** level@1 7/76: 11 goldens have no live level at
   τ (generation absence) and 57 wrong picks (40 >10 p off) — the
   right level is never live, selection cannot rescue (1/57 at rank-2).

## Provenance

- C-1 keeps K1–K6 verified at `9acaa206` (GATE_PACK_C1).
- K7 verified: `81f7503f` (clutter 5.00→4.67, margin +13, level +1).
- K8 verified: `be4eea26` (box +1, level +1, clutter flat).
- K9 verified: `ee2cbf12` (M1 flat, clutter 4.67→4.33, margin +13).
- F1: `_scratch/perf/` → `v2/` merge, 1728/1728 + 20d DESIGN identical;
  55-day throughput 32→104 bars/s day-54.
- C-2 = `4c2df34d7a2a8ee3` (K1–K9 + F1 merged).
- C-3 = `1a5502129b4c1554` = `uip2_pbbirth`@`8361fe85` folded:
  box +6 to v0 parity, level −1, line flat, clutter flat, suite 72/72.
  Rejected sibling arms: `uip_on` (box −3, level −4), `uip2_on`
  (box parity, level −4 — the lvfree exclusions are what keep level),
  `uip2_lvfree_pb` (inert vs V1), `uip2_bs` (byte-flat — buildstart
  instrumentation only), `box_v0_family` option-B port (prepared,
  byte-identical vs standalone v0, no A/B per R64).
- Migration Phase A (post-C-3, all identity-verified): A1 `18ea3147`,
  A2 `033aad2b`, A3 `ba1b9532`, A4 `e1775edd`, A5 `63148cff`,
  A6 reverted (review BLOCK) → tree `2d497427543f9d86`,
  full canonical 623/623 identical vs C-3 cache.
- Rejected C-2 arms: ctx_yield ×3, ctx_convert ×2, bmday, wick_birth,
  lnsf42, deeper_w (lab), cong_subband (lab), X1 pivot-score term.
