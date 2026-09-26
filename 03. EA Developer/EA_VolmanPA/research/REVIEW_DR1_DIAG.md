# REVIEW_DR1_DIAG — neutral review rounds for T-VPA-DR1-DIAG

Reviewer: independent subagent (general), read-only + light csv/arithmetic, cwd
`03. EA Developer/EA_VolmanPA`. Two rounds, budget respected (≤2).

## Round 1 — VERDICT: FAIL

Checks (mandatory): 1 case→timestamp mapping, 2 trace shares code, 3 discrimination
recomputable, 4 no outcome fields, 5 book cites.

- CHECK 1: **PASS** — 6 PNG titles vs `snapshots/INDEX.csv` vs `KEY_HIDDEN.csv`
  (case_003 10:10 short A; 012 16:40 long A; 020 12:40 short B; 065 08:05 short B;
  154 16:15 long B; 196 16:20 long B); join over all 10 `ab_*.png` rows: bar_idx
  mismatches NONE. (case_025 `barrier` differs by design: INDEX = trace
  `dr1_barrier` 1.188545 vs KEY case barrier 1.188715.)
- CHECK 2: **PASS** — `vpa_trace.py:15 from vpa_dr1 import Dr1Detector, full_fail_set
  # noqa: F401 (shared gate path)`; no `def _dr1_gates`/`def verdict_from_gates` in
  vpa_trace.py; detector path `vpa_dr1.py:351 gates = self._dr1_gates(sig, bar)` →
  `:383 ok, reason = verdict_from_gates(gates)`; test at `test_vpa_dr1.py:282-306`.
  Reviewer re-ran the suite: `PASS trace_equals_detector candidates=2860 mismatches=0`
  / `PASS benchmark_real_eurusd 9.9s bars=440040 records=19957 executable=1
  medATR=3.41p` / `TESTS PASS 45/45`.
- CHECK 3: **FAIL** — recomputation from `RECALL_TRACE.csv` reproduces
  `RECALL_SUMMARY.md:49-58` exactly (DR1 config, evaluated A/B n=4, C n=19) but all
  10 gate rows differ from `DISCRIMINATION_DR2C.md:7-16` (DR2c, A/B n=15, C n=34).
  Doc provenance was stated, but no DR2c per-case trace had been shipped.
- CHECK 4: **PASS** — word-boundary grep (pnl|profit|win|loss|mfe|mae|r_multiple|
  fill|outcome|result) over all diag artifacts: only the disclaimer prose
  `RECALL_SUMMARY.md:3 ... No outcome fields (E4).`
- CHECK 5: **PASS** — all 5 changes in `VPA-DR2_PROPOSAL.md` §4 carry cites:
  (1) tr. 88, 95; (2) tr. 227, 273; (3) tr. 167, 43; (4) tr. 103, 223;
  (5) tr. 95. RULEBOOK.md:14/17/114 and page_043.jpg / page_223.jpg verified.

Claim checks: "4/16 → 15/16" TRUE; "DR2c exec=4, 0.0128/tuần" TRUE (4/312.7);
"DR2e 5,528 = 17.7/tuần, A/B 10, C 8" TRUE.

Open issues (round 1): 1) DR2c discrimination not recomputable (→ fixed);
2) `snapshots/INDEX.csv` config is DR2a, not comparable to `RECALL_TRACE.csv` (DR1);
3) INDEX `barrier` = `dr1_barrier` (documented); 4) proposal "55%" without
denominator (→ fixed to 10/18).

## Round 2 — VERDICT: PASS

- FIX 1: **PASS** — `RECALL_TRACE_DR2C.csv` (61 lines = header + 60 rows, unique
  case_id 60); recomputed cell-by-cell vs `DISCRIMINATION_DR2C.md:9-18`
  (warmup 0/15|0/34; session 1/15|1/34; direction 3/15|10/34; trend 2/15|24/34;
  chop 5/15|4/34; buildup 11/15|22/34; room 4/15|12/34; adverse 4/15|11/34;
  anti_chase 4/15|3/34; cost 0/15|0/34) → `differing_cells: NONE`.
- FIX 2: **PASS** — doc now states its source CSV and that `RECALL_TRACE.csv`
  (DR1) does not reproduce the table.
- FIX 3: **PASS** — "10/18 ≈ 55%" wording + §7 snapshot-config note; residual
  lines 127/143 also fixed after round 2 (10/18 restated).

Verdict: deliverables accepted. Remaining non-blocking notes: the burned set
(E3) is diagnostic only; n(A/B)=16 has wide CIs; DR2e is a technical bound, not a
recommended config.
