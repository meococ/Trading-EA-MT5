# GATE_PACK_C3 — C-round-3 close pack (EVAL-AUDIT)

Generated 2026-09-23 04:29Z by EVAL-AUDIT's own scorer (m1_row.py), TUNE 198 panels, ruler `50e11fd5a2ab7974`.

STABLE C-3: `1a5502129b4c1554` = STABLE C-2 `4c2df34d` + keep `uip2_pbbirth` (folded into params_v1_1.json defaults: salience.ev_uip, ev_uip_persist, ev_uip_lvfree, ev_uip_pb_birth = True; pb_write/buildstart/box_v0_family stay OFF). The measured row below is `uip2_pbbirth@8361fe85`; the folded default engine was verified byte-identical to it on all 198 TUNE panels (objects+cand_log+events, evalcheck/_c3_freeze_check.py).

## M1 — per-family recall at the author's budget

| arm | box@1 | level@1 | line@2 | bracket@1 † |
|---|---|---|---|---|
| v0 `63c771d6` | 0.134 (16/119) | 0.066 (5/76) | 0.093 (18/193) | 0.388 (33/85) |
| STABLE C-3 | 0.134 (16/119) +0.000 [-0.104..+0.104] | 0.092 (7/76) +0.050 [-0.028..+0.133] | 0.104 (20/193) +0.015 [-0.040..+0.070] | 0.341 (29/85) -0.015 [-0.172..+0.134] |
| C-2 parent | 0.084 (10/119) | 0.105 (8/76) | 0.104 (20/193) | 0.341 (29/85) |

† bracket@1 reported, not part of M1. CIs are paired day-bootstrap of (arm − v0), seed 20260921, 1000 resamples.

## Clutter + diagnostics (STABLE C-3)

- today's def (window census): clutter ratio median **4.33** (parent 4.33, v0 9.00); 110/179 scored panels <= 5.0 (parent 114)
- BOX recall 0.111 | BOX precision 0.041 | PATTERN_LINE recall 0.114 | LEVEL_CARRIED recall 0.188 | LABEL_TF agreement 0/2
- event-route births: exactly 1.0/panel | live box-family objects at window end: med 2.0 (parent 1.0)

## Option-C row (information only; ruler unchanged)

Live-at-τ clutter (_live_clutter_c3.py; STRICT = ACTIVE at τ, LOOSE = not-DELETED):

| arm | strict med | strict margin | loose med | loose margin |
|---|---|---|---|---|
| C-2 parent | 2.00 | 166/179 | 3.50 | 128/179 |
| v0 | 2.67 | 150/179 | 6.83 | 53/179 |
| hybrid v1+v0box | 2.00 | 167/179 | 4.25 | 111/179 |
| **STABLE C-3 (uip2_pbbirth)** | **2.33** | **163/179** | **3.89** | **125/179** |

## Suite of record (unmodified research/perception/tests/, 72 collected)

- **STABLE C-3 params: 72/72 PASS** — `test_pullback_end_box_birth` cured (pb candidate births the UIP object at v0's route gate idx−t0a≥3); the six other named fixtures stay cured by the lvfree decoupling.
- C-2 parent params at same tree: 65/72 (the named seven).
- Build's earlier "67/67" was a wrong-directory collection (PA_Pro/tests/, EA-exec suite), corrected by build 03:56Z; the 72-test perception suite is the suite of record (R68 s.68.2).

## Flipped box-family goldens vs C-2 parent (rank-1 hit)

- gained 15: 9.11a(CONTEXT_RANGE) 9.13a 9.15b(t900) 9.17a 9.18a 9.27a 9.32a(t478) 9.32a(t510) 9.34a 9.41b 9.44b 9.45a(t350) 9.58a 9.61b 9.7b
- lost 9: 9.14a(RANGE_OPEN) 9.15b(t895) 9.25b 9.2b 9.36b 9.39a 9.45b 9.48b 9.4b
- level flips vs parent: +1 (9.5c) / −2 (9.49a, 9.56b) = net −1

## Keep chain + identity

- C-3 = C-2 (9acaa206 + K7 + K8 + K9 + F1) + uip2_pbbirth. OFF-identity evb_off@8361fe85 vs c1r_p_base@ee2cbf12: 1728/1728 objects+cand_log+events canonical identical (141 unshared rows).
- Snapshot `_scratch/freeze_candidates/1a5502129b4c1554/` recomputes to the stable hash exactly (kernel.py excluded — it postdates the fold, added to V1_FILES during ARCH migration A1).
- Post-freeze ARCH migration A1 (kernel.py extraction, 18ea3147+) verified identity-clean on all 198 TUNE panels vs the measured arm — same pass that confirmed the params fold.

## Status

C-round 3 closed STABLE `1a5502129b4c1554` at ~04:17Z. First config in the programme meeting M1 on all three families at the author's ink (box ties v0 exactly — zero box margin). The suite of record is fully green. Pending: Owner's Decision-C next steps (human-ceiling kit, M2 blind-precision pack on this STABLE); ARCH Phase A refactor proceeds step-by-step under OFF≡parent identity checks; BOX-LAB §67.4 reach channel; DR-LINE essence research (R69).
