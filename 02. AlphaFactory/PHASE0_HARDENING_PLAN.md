# PHASE 0 HARDENING PLAN - AlphaFactory + MT5 End-to-End

**Date locked:** 2026-03-06  
**Owner:** Max  
**Purpose:** harden the workspace so Max can operate as the **primary end-to-end MT5/MQL5 agent** for coding, compile, backtest, analytics, forensic review, and research memory.

---

## 1) Mission

Build a deterministic, MT5-first, research-safe workflow that is:
- **Correct** for MT5/MQL5 behavior
- **Smart** in research and forensic reasoning
- **Efficient** in execution and iteration speed
- **Persistent** across future chat sessions

This phase must happen **before** trusting the stack for large EA build cycles.

---

## 2) Non-negotiables

1. **AlphaFactory local is the primary executor** for compile/backtest/analyze.  
   `max-control` is fallback only, not the default lane.

2. **One run = one change** for all meaningful experiments.

3. **Local artifacts win** over memory or external summaries.  
   Priority:
   1. repo files + run artifacts  
   2. `STRATEGY_LOG.md`  
   3. MCP memory / notes  
   4. external summaries / search

4. **Official docs win** for MT5/MQL5 API or tester behavior.

5. **Closed-bar / no-lookahead by default** unless explicitly testing tick-mode behavior.

6. **Single-writer rule** on run artifacts and analysis phases.

7. **No "fake robustness" claims.**  
   Trade-perturbation tests are useful as quick screens, but must be labeled as such.

---

## 3) Phase 0 workstreams

## W1. Execution Authority & Artifact Contract

### Goal
Remove ambiguity about who runs what, where outputs go, and which artifacts are authoritative.

### Actions
- Lock default lane to:
  `alpha-orchestration-guard -> alpha-ea-runner -> alpha-report-analyzer -> alpha-datalog-db -> alpha-execution-quality -> alpha-regime-buckets -> alpha-parameter-sensitivity -> alpha-walk-forward -> alpha-monte-carlo -> alpha-robustness-suite -> alpha-correlation-exposure -> alpha-strategy-memory`
- Standardize run subfolders:
  - `analysis/`
  - `analysis/datalog/`
  - `robustness/`
  - `walk_forward/`
  - `sensitivity/`
  - `regime/`
  - `trade_charts/`
  - `correlation/`
- Add a small `run_manifest.json` for each run with:
  - EA / symbol / TF / dates / model
  - overrides
  - source report
  - artifact paths
  - timestamps

### Acceptance
- Same run can be re-opened later without guessing paths.
- No analyzer writes into ad-hoc folder names.

---

## W2. MT5 Runner Reliability & Isolation

### Goal
Make backtesting safer for MT5 and less destructive to parallel/manual terminal usage.

### Actions
- Move toward a **dedicated tester lane**:
  - dedicated MT5 tester instance/profile if practical
  - isolate tester cache and `Common\\Files` usage per run
- Reduce global side effects:
  - avoid broad cache deletion unless needed
  - avoid deleting unrelated `.set` or logs outside the test lane
- Keep compile-first rule explicit, even if runner can auto-compile
- Improve main-file selection so the intended EA entry point is unambiguous
- Add smoke self-check after run:
  - report exists
  - datalog copied
  - analysis written

### Acceptance
- Backtest lane is deterministic.
- Manual MT5 usage is not accidentally broken by routine tests.
- Failed runs explain whether failure came from compile, MT5 launch, timeout, missing report, or missing logs.

---

## W3. Analyzer Correctness for Multi-Position / Multi-Engine EAs

### Goal
Make analysis safe for modern EAs with add-ons, partials, overlapping positions, and multiple magic families.

### Actions
- Replace report trade aggregation that assumes “one position at a time”
- Pair deals using:
  - `position_id`
  - `order_id`
  - deal direction
  - volume reconciliation where needed
- Add consistency checks:
  - report trades vs datalog trades
  - net PnL agreement
  - close-reason agreement
- Support overlapping positions and portfolio-style runs
- Add timezone handling:
  - broker/server time
  - UTC or explicit offset mode

### Acceptance
- Trade counts and trade-level metrics remain valid for multi-engine EAs.
- Session/hour analysis is not silently shifted by timezone mismatch.

---

## W4. Visual Forensics Layer

### Goal
Make chart review part of the default quant workflow, not an afterthought.

### Actions
- Keep `analysis_charts.png` available as standard output when requested
- Integrate `trade_chart_capture.py` into the routine workflow
- Add standard trade chart outputs:
  - worst losers
  - best winners
  - selected anomalies by close reason / session / engine tag
- Ensure output index is machine-readable:
  - `trade_charts/trades_index.json`
- Use image review tooling to let Max inspect:
  - equity curve shape
  - drawdown clusters
  - trade timing and local market structure around entries/exits

### Acceptance
- Every serious run can be reviewed via equity chart + per-trade snapshots.
- Visual forensics can support execution-quality conclusions, not only KPIs.

---

## W5. Robustness & Research Integrity

### Goal
Separate quick heuristics from higher-confidence validation.

### Actions
- Treat trader-style lifecycle playbooks as **hypotheses**, not truth, until supported by artifacts.
- Add lifecycle analytics requirements:
  - MFE / MAE by engine and setup tag
  - time-to-0.3R / 0.5R / 1R / 2R
  - profit giveback from MFE to realized exit
  - overnight / rollover / Friday / weekend exposure outcomes
  - swap cost by symbol / direction / engine
  - close-reason distribution after profit-lock logic
- Mark current trade-perturbation tests as:
  - `quick_screen`
  - not final deployment proof
- Preserve and use:
  - Monte Carlo
  - regime buckets
  - datalog gate analysis
- Improve or backlog:
  - true parameter reruns
  - more faithful WFA / re-optimization loops
  - portfolio correlation analysis
- Add `correlation_exposure.py` for:
  - overlap
  - same-direction clusters
  - daily PnL correlation

### Acceptance
- Reports clearly distinguish between:
  - fast heuristics
  - stronger validation layers
- Trade lifecycle rules can be traced to concrete data, not only trader intuition.
- No future session overstates what the current robustness scripts actually prove.

---

## W6. Memory & Session Persistence

### Goal
Ensure future chats load this doctrine automatically.

### Actions
- Persist this Phase 0 file in repo
- Add persistent instruction in `AGENTS.md` to read and follow it
- Add meta note to `STRATEGY_LOG.md`
- Add persistent auto-research doctrine so Max proactively verifies valuable external information without waiting for reminders
- Reuse the doctrine for all future EA projects in this workspace

### Acceptance
- New chat sessions inherit the same operating doctrine automatically.

---

## W7. Performance & Iteration Efficiency

### Goal
Keep the workflow fast enough for frequent ablations without sacrificing correctness.

### Actions
- Prefer incremental/batched analysis after run completion
- Avoid unnecessary full-folder scans
- Make chart generation optional but easy to enable
- Keep debug logs useful, not spammy
- Reuse copied artifacts instead of reparsing when nothing changed

### Acceptance
- Routine compile/backtest/analyze cycles stay lightweight.
- Heavy visual or portfolio steps can be turned on deliberately, not by default.

---

## 4) Phase 0 Priority Order

## P1 - Must fix early
1. Lock executor doctrine and artifact contract
2. Fix multi-position report parser
3. Integrate trade-chart capture into workflow
4. Add timezone-safe analysis
5. Persist doctrine into `AGENTS.md` + `STRATEGY_LOG.md`

## P2 - Strongly recommended
6. Add correlation exposure automation
7. Improve MT5 tester isolation
8. Add run manifest
9. Label quick-screen vs stronger validation in outputs

## P3 - Next refinement
10. Dedicated tester instance/profile
11. True optimization / stricter WFA upgrades
12. Extra forensic chart bundles and anomaly galleries

---

## 5) Default Operating Doctrine After Hardening

When building or evaluating any EA in this workspace:

1. Read:
   - `AGENTS.md`
   - this Phase 0 file
   - relevant run artifacts / strategy memory
2. Compile first
3. Backtest with explicit overrides
4. Analyze report + datalog
5. Audit non-repaint / execution / regime behavior
6. Review equity curve + trade charts when investigating quality
7. Only then log conclusions to memory

---

## 6) Definition of Done for Phase 0

Phase 0 is considered done when:
- Max can run the whole lane **without ambiguity**
- artifact locations are standardized
- report parsing is safe for multi-position EAs
- trade charts are operational
- time/session analysis is timezone-aware
- correlation exposure has automation
- future chat sessions automatically inherit this doctrine

---

## 7) Short reminder for future sessions

If a new session starts and the user asks to build or review an EA:
- do **not** jump straight into strategy logic
- first check whether the request touches Phase 0 constraints
- preserve MT5 correctness, reproducibility, and research integrity
