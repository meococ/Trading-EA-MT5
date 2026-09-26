# R02 PROGRESS — resume log (UTC)

One line per completed step: `UTC | step | status | key files`. Append only.

2026-09-20T17:40Z | A-F2 | OK | token gate repaired (closure-held mint/check, per-session nonce, split binding, one-shot private handshake, raising decoys); tests/test_eval_gate_bypass.py (3 tests) | lib/pa_eval.py, lib/pa_metrics.py
2026-09-20T17:45Z | A-F3 | OK | refs.py daily carry-forward fixed; impact measured (1,577 -> 445,595 bars; 18-43% of frozen events shift, tercile moves 2.2-10%); FREEZE_ADDENDUM entry | struct/zones/refs.py, rounds/R01/FREEZE_ADDENDUM.md, research/physics/tests/test_refs_carry_forward.py
2026-09-20T17:50Z | A-F4 | OK | gate_verdict 3-of-3 fallbacks deleted | research/physics/phys_stats.py, research/physics/tests/test_gate_verdict.py
2026-09-20T17:52Z | A-F5 | OK | freeze-ordering guard implemented | research/physics/phys_analysis.py, research/physics/tests/test_freeze_guard.py
2026-09-20T17:55Z | A-F9 | OK | ledger tail sidecar (last-line tamper now detected; pre-fix ledgers bootstrap once) | lib/pa_ledger.py, tests/test_ledger_tail.py
2026-09-20T17:57Z | A-F10/F11 | OK | run_counts signature fixed; ctrl/resolved + mean K/event column fixed | research/physics/run_counts.py, research/physics/phys_analysis.py, research/physics/tests/test_run_counts_signature.py
2026-09-20T18:00Z | A-suite | OK | tests/ 43 -> 49 passed; research/physics/tests 31 -> 40 passed; real ledger verify (True, None) with sidecar
2026-09-20T18:02Z | A-report | OK | rounds/R02/REFEREE_FIXES.md written; no physics/eval run, no commit, no push
