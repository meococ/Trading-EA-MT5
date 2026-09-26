# STATUS — VPA-DR1 (T-VPA-DR1)

Updated: 2026-09-20 (task closeout)

| Phase | Trạng thái | Ghi chú |
|---|---|---|
| 0. Lead decisions saved | DONE | `research/LEAD_DECISIONS_DR1.md` (verbatim D1–D6). |
| 1. Prereg frozen | DONE | `research/VPA-DR1_FROZEN_PREREG.md`, SHA256 `36F1AFAC76A47CE016B886475EBFBB28F1CA0DC79D8ADD48708E6B5F82944D62`, mtime 14:24:03 < census outputs. Includes D1–D6, the D1d 2.0R rationale, gates and trial budget. |
| 2. Implementation | DONE | `research/lab/vpa_dr1.py` (Dr1Detector): signal-bar decision, stop-entry 1 pip beyond the signal bar, D1a direction rule, trend/buildup/chop/room/adverse/anti-chase/cost gates in the prereg order, Combi only as a classification inside a valid PB context. |
| 3. Tests | DONE | `research/lab/test_vpa_dr1.py` + `fixture_dr1.py`: **43/43 PASS** (per-gate positives, one negative per gate, overlap/contraction negatives, direction rule, combi context, non-vacuous prefix invariance, deterministic replay, real-data benchmark 13.9s/440k bars). |
| 4. Census | DONE | `PLAN/census_dr1/` CSV/JSON/SUMMARY: **1 executable / 314 weeks = 0.0032/week** → D2 rule = **STOP (<3/week)**. Funnel: 45,073 barriers → 19,957 signal evals → 15,276 outside session → 4,681 in-session evals → 3,312 unique in-session candidates (10.6/week) → gates (trend 2,752; room 779; buildup 635; chop 284; direction 202; anti-chase 26; adverse 2) → 1 executable. No outcome fields anywhere. |
| 5. Grading at scale | SKIPPED | Per D2 STOP (<3/week): no snapshots, no G1/G2/G3, no FIDELITY_DR1. |
| 6. A5 AC1 fix | DONE | `pe /= (K-1)` in `vpa_calibration_v2.py`; re-emitted `CALIB_V2_RESULTS.txt`; `CALIBRATION_V2.md` updated: 3-class 0.742 / 0.667 / 0.483, binary unchanged 0.770 / 0.606 / 0.467. |
| 7. Neutral review R2 | DONE | Round 1: VERDICT PASS, 12/13 VERIFIED (92.3%), 0 CRITICAL, findings F1/F2/F3/F5. Fixes applied; round-2 re-review appended to `research/REVIEW_DR1.md`. |
| Blockers | — | Cadence STOP per D2: DR1 baseline is not viable; DR2 direction recommended in `CENSUS_DR1_SUMMARY.md §5`. |

# STATUS — VPA-DR1-DIAG (T-VPA-DR1-DIAG)

Updated: 2026-09-20 (task closeout)

| Phase | Trạng thái | Ghi chú |
|---|---|---|
| 0. Lead decisions saved | DONE | `research/LEAD_DECISIONS_DIAG.md` (E1–E5 verbatim + burn record). |
| 1. Trace infra | DONE | `vpa_dr1.py` single gate path (`_dr1_gates`/`verdict_from_gates`/`full_fail_set`); `vpa_trace.py` shares it; `test_trace_equals_detector` (2,860 candidates, 0 mismatches) + `test_trace_module_shares_code` → **45/45 PASS**. DR1 defaults behavior-identical (records 19,957; exec 1; counters unchanged). |
| 2. Recall trace | DONE | 60 burned cases (A/B=16, C=44): (i) 11, (ii) 26, (iii) 23, (iv) 0. DR1: 11/16 A/B never evaluated; 9 of them = "missed break" at the case bar itself. `PLAN/diag_dr1/RECALL_TRACE.csv|RECALL_SUMMARY.md`. |
| 3. Root causes | DONE | D1 signal bar = last **touch** bar (not close-at-B): A/B (ii) 11→0; D2 session windows narrowed vs the graded v1 universe (9/16 A/B outside DR1 windows); D3 only `trend` discriminates (13% vs 71%); buildup/chop/anti-chase fail A/B more than C. |
| 4. DR2 candidates | DONE | `PLAN/diag_dr1/DR2_VARIANTS.csv|md`: DR2a/b/c/d = 0.0096–0.0128/week (bar 3/week NOT met); DR2e bound (trend only) = 17.7/week, 10/16 A/B, 8/44 C. `RECALL_TRACE_DR2C.csv` + `DISCRIMINATION_DR2C.md`. |
| 5. Snapshots | DONE | `PLAN/diag_dr1/snapshots/` 20 PNG (10 A/B + 10 missed-break) + INDEX.csv (config DR2a). |
| 6. Proposal | DONE | `research/VPA-DR2_PROPOSAL.md` — 5 changes with book cites; decision (A) STOP per D2 vs (B) DR3 score-based left to Lead/Owner. |
| 7. Neutral review R2 | DONE | Round 1 FAIL (CHECK 3: discrimination not recomputable from the shipped trace) → fixed by shipping `RECALL_TRACE_DR2C.csv`; round 2 **VERDICT PASS**; both appended to `research/REVIEW_DR1_DIAG.md`. |
| Blockers | — | No AND-stack variant reaches 3/week; lane fate = Lead/Owner decision (proposal §5). |

# STATUS — VPA-DR3 (T-VPA-DR3)

Updated: 2026-09-20 (task closeout)

| Phase | Trạng thái | Ghi chú |
|---|---|---|
| 0. Time sanity (F4) | DONE | `PLAN/dr3/TIME_SANITY.md`: `utc_min` thiếu wrap → 41,449 bar âm (missed_04 = `-1:15`); fix `(srv_min - off*60) % 1440`; 0 session change; 3 timestamps (winter/summer/DST) verified. |
| 1. Lead decisions | DONE | `research/LEAD_DECISIONS_DR3.md` (F1–F7 verbatim). |
| 2. Prereg frozen | DONE | `research/VPA-DR3_FROZEN_PREREG.md`, SHA256 `A61F06BA776BD0D74A94FBFD243ECFFC9C880988832BAEC789F50DAA675E05A2`, mtime 16:42:48 < mọi output census/grading. |
| 3. Code + tests | DONE | Integrity gate (F2c) + DR3 hard-gate subset trong cùng gate path; features (buildup 4-cond/2-of-4/tight, chop window, room zone-excluded, adverse, anti-chase, squeeze, pressure, lunch, rho). `TESTS PASS 52/52` (integrity +/-, room-zone, chop-window, buildup variants, DR3 cfg, trace == detector). Look-ahead significant-pivot đã fix causal (`j = t - S`). |
| 4. Census (F6) | DONE | `PLAN/census_dr3/`: **4,331 accepted = 13.85/week → NORMAL** (≥10); funnel trend 22,010 / integrity 3,439; per-year 668–744; eu 2,055 / us 2,276; feature distributions + burned diagnostic (DIAGNOSTIC-ONLY: A/B accepted 9, C 8; integrity removes A/B 3, C 13); no outcomes. |
| 5. Fidelity (F5) | DONE | `PLAN/grading_dr3/`: 180 blind (120 accepted + 60 rejected = 51 trend + 9 integrity), 30/year, min distance 52 bars from burned cases; G1/G2 hashed before unblind (5bef16c7…, 7df3c09a…); G3 on 60 disagreements (21/21/18). **dual +56.0pp [+38.9,+67.5] PASS; majority +43.3pp [+28.2,+55.4] PASS; A/B accepted 70.0% ≥ 40% → F5 GATE PASS**. `LEAD_SPOTCHECK_INDEX.csv` 20 blind (12 accepted + 8 rejected). |
| 6. Neutral review R2 | DONE | `research/REVIEW_DR3.md`: round 1 tìm look-ahead (significant pivot đọc t+3) → fix causal; round 2 **VERDICT PASS 7/7** (burned exclusion 52 bars, DRAW_QA 180/180, fidelity recomputable, provenance/no-leak, no outcomes, prereg order, tests 52/52); 3 open issue nhỏ đã fix + re-verify. |
| Blockers | — | Không. DR3 đạt cả F6 (cadence) và F5 (fidelity) — chờ Lead/Owner quyết bước tiếp (MQL5 port/DR4 features). |

# STATUS — VPA-ECON-1 (T-VPA-ECON-1)

Updated: 2026-09-20 (task closeout)

| Phase | Trạng thái | Ghi chú |
|---|---|---|
| 0. Time/prereq recon | DONE | Cost evidence `PLAN/COST_FEASIBILITY.md:75` (c_rt p90 EURUSD 1.0p); HYP gates; NEWS: NOT AVAILABLE (`PLAN/econ1/NEWS_CALENDAR_RESEARCH.md`, fallback windows [745,765)/[805,825) UTC). |
| 1. Prereg frozen | DONE | `research/VPA-DR3_ECON1_PREREG.md`, SHA256 `644DBCBA91B9859AF5989068BB9C7D8CAB034CBCE99675554B48938C5BE9663`, mtime 17:52:06 < mọi file `PLAN/econ1/*`; Addendum A1 ghi correction SHA của engine (session-end cancel) trước outcome. |
| 2. Engine + tests | DONE | `vpa_econ1_sim.py` (V=3, invalidation cancel, session-end cancel, gap-aware fill, SL-first, flats 22:00/20:00 server, midnight) + `test_vpa_econ1_sim.py` **19/19 PASS** (hand-computed fixtures); matched-random `vpa_econ1_random.py` 6/6. |
| 3. ONE verdict run | DONE | 4,331 signals → 2,436 fills; cost scenarios gross/x1/x1.5/x2; matched random K=20 → 42,257 fills; `PLAN/econ1/TRADES_DESIGN.csv`, `RANDOM_MATCHED.csv`, `ECON1_METRICS.json`. |
| 4. Verdict (G6) | **FAIL** | PF x1 0.795 (<1.30), x1.5 0.720, x2 0.667, gross PF 0.992 (<1.10); N 2,436 PASS; DD 84.2% (>6%) FAIL; b 1.839 PASS; **LIFT x1 +0.24pp (CI [-1.61,+2.14]) và x2 +1.49pp (CI [-0.29,+3.34]) — không phân biệt được với matched random** → 6/9 gate FAIL. `PLAN/econ1/ECON1_RESULTS.md`. |
| 5. Neutral review R2 | (đang chạy) | `research/REVIEW_ECON1.md`. |
| Blockers | — | DR3 không có edge kinh tế trên DESIGN; Lead escalate Owner (G6). VAL/OOS/HOLDOUT chưa mở (G5). |
