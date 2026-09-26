---
name: loop
description: AlphaFactory continuous research→probe→prereg→build→governed-run→verdict→learn cycle. Self-fixing via the known-trap playbook. Heuristics banned.
argument-hint: "[max_iterations=N] [direction hint]"
triggers:
  - user
  - model
---

# /loop — AlphaFactory continuous EA campaign loop

Placeholders: `<REPO_ROOT>` = thư mục gốc repo trên máy đang chạy (local hoặc Devin cloud VM); `<OWNER_GUI_TERMINAL>` = MT5 GUI của Owner — chỉ trên máy Owner.

Runs the governed hypothesis cycle until the GOAL contract is met, all legal
directions are exhausted, or max_iterations is hit (default 1 — say so when
stopping). Report at each iteration boundary; continue without asking unless
a HARD STOP condition fires.

Authority: Owner request > `01. GOAL/GOAL.md` > attempt contract > verified
artifact > registry. `04. Memory/hot.md` is cache, never authority.

---

## HARD BANS (cấm heuristic — never violated)

- NO minting/building an EA before Stage-0 evidence AND a frozen prereg exist.
- NO parameter tweaks after observing governed results — a changed mechanism
  is a NEW hypothesis with its own frozen prereg, and the post-observation
  basis must be declared in it.
- NO resurrecting killed families/mechanisms without NEW evidence; the kill
  reason is recorded — address it or stay dead.
- NO lookahead: levels/signals/triggers use only bars closed before the
  decision point. Re-verify strict prior-day/session semantics on every
  probe (the `dk-1 <= day <= dk` bug already cost one fake campaign).
- NO reading PF of an exit-conditioned subset as mechanism evidence
  (selection-on-survival artifact — HYP-001's "PF 2.42 subset" was this).
- NO trading live, NO `mt5.initialize(path=...)`, NO bare `terminal64.exe`,
  NO `mcp__mt5__trade_*`. Compile/backtest ONLY via `alpha.ps1` /
  `ea_research_loop.ps1` on the portable isolate.
- NO commits/pushes unless Owner asked in the current message.
- NO removing safety layers to manufacture passes (news blackout,
  daily-flat, sizing/margin checks stay; DD-lock may be disabled only if
  the prereg declares why — it distorts the measured mechanism).
- If Stage-0 evidence is weak or the mechanism is not causal, KILL it in
  the probe — do not "try it in the tester anyway".
- NO trusting probe prices inside burst regions (roll 00:00-00:10 server,
  news minutes): `hcc_reader` phase-scan fabricates records there. Any
  entry/exit price in a burst window must match real fills/ticks
  (HYP-RGR-001: "PF 4.3" probe edge was fabricated, governed PF 0.14).

---

## ITERATION CYCLE

### Phase 0 — State load (every iteration)

- Read `01. GOAL/GOAL.md` gates verbatim (PF>1.30 x1, x1.5>=1.25, x2>=1.00,
  cadence 10-40/wk/symbol, HQ>97, no weekend, limited overnight).
- Scan `04. Memory/research/CANDIDATE_REGISTRY.jsonl`: states, verdicts,
  killed families, pending hypotheses. Validate if edited
  (`04. Memory/research/validate_candidate_registry.py` runs inside the loop).
- Read `04. Memory/hot.md` tail for the current trap/lesson list.
- Kill orphan isolate terminals (`terminal64.exe` under
  `02. AlphaFactory/runtime/` only — never the Owner GUI
  `<OWNER_GUI_TERMINAL>`).

### Phase 1 — Direction selection (declared before probing)

- **GATE D**: Alpha Researcher (`/.devin/agents/alpha-researcher.md`) ranks
  candidate classes; GOAL Gatekeeper states the binding constraint.
- List mechanism CLASSES already falsified (registry kill table). Pick a
  class NOT yet falsified, or a surviving anomaly family with untested
  cells — rank by: causal story, expected cadence vs band, cost structure,
  published/repo evidence.
- With-trend entries are favored over counter-move entries: governed fills
  at next-bar-open are ADVERSE for fades but FAVORABLE for continuation —
  the probe-vs-governed gap cuts opposite directions.
- Declare in the prereg/probe notes WHY this direction and what would
  falsify it.

### Phase 2 — Stage-0 probe (cheap kill first)

- Attach via `factory_paths.mt5_initialize_kwargs()` only; chunked
  `copy_rates_from` (range copies fail across stub .hcc gaps);
  `symbol_select` + warm-up retry on fresh terminals.
- Required: split-half same-sign validation, per-year stability check,
  event cadence, and BOTH gross and net-of-cost expectancy.
- **Governed-discount rule**: expected net = probe_edge − (measured RT
  spread+slip+commission) − (adverse-fill gap: ~1-3 pips for counter-move,
  ~0 or positive for with-trend). Probe must still clear threshold AFTER
  discount. If it can't survive realistic fills, kill here.
- Multiple-testing control: with C cells tested require |t|>~2.8 in BOTH
  halves before calling anything an anomaly.
- Probe files live in `02. AlphaFactory/tools/probe_*.py`; comment the
  level semantics (which bars are "prior") to prevent lookahead
  recurrence.
- **GATE A (mandatory before prereg)**: Data-Integrity Auditor +
  Quant Methodologist review the probe output. Both PASS required —
  a probe edge that survives stats but not fill-level validation is dead.

### Phase 3 — Frozen prereg + screened registry row

- Write `03. EA Developer/<EA>/research/<HYP-ID>_FROZEN_PREREG.md` BEFORE
  any governed outcome for the new hypothesis. Contents: falsification
  context, evidence, exact mechanism (entries/exits/sizing/filters),
  environment, honest cadence expectation, kill criteria.
- **GATE B (mandatory before freeze)**: Adversarial Auditor +
  GOAL Gatekeeper review the prereg draft. Both PASS before freezing.
- Append screened row to `CANDIDATE_REGISTRY.jsonl` with FULL schema:
  `verdict:'SCREENED_PENDING_RUN'`, `reason`, `metrics:{}`, `validation`,
  `updated_at_utc`, `window` bound to VERIFIED coverage (never sentinel
  1970 unless `all_available_asof` HQ-proven), `source_hash`,
  `prereg_sha256`, and `exact_overrides` = ALL spec params pinned in
  canonical sorted order (InpAbc=…;… alphabetically — the engine
  normalizes the CLI the same way; unpinned params get silently replayed
  from tester `.set` memory).

### Phase 4 — Build / fix EA

- Package under `03. EA Developer/`; reuse `_Shared` substrate:
  `AF_ExecutionKernel`, `AF_LifecycleTelemetry`, LSW clock/session/risk.
- Closed-bar decisions; every signal has caller+state transition+
  telemetry+exit path; no dead helpers.
- Non-repaint audit conformance: any `CopyRates/CopyBuffer/CopyTime`
  shift arg must be a bare param guarded by `if(param<1) return` inside
  the SAME function (`allowed_guarded_shift_param`) — computed locals
  fail; use a guarded helper like `BeCopyClosedM5`.
- `alpha.ps1 compile <EaName>` must yield fresh log `0 errors, 0 warnings`
  + new EX5.
- **GATE E (optional)**: MQL5 Architect review for new substrate use or
  audit FAILs — before compile when practical.

### Phase 5 — Packet + governed run

- Cost evidence via `measure_cost_evidence.py --out-dir … --end-utc
  <ISO-Z inside run window>` → manifest bound by `build_control_packet.py`.
- `build_control_packet.py` args mirror the row: `--history-quality`,
  `--bars`, `--ticks`, `--from-date`/`--to-date` = VERIFIED identity
  (from a prior report/discovery run; new symbols need one discovery run
  first — post-run fingerprint check only fires after).
- `ea_research_loop.ps1` with `-Execute`, `ALPHAFACTORY_FORCE_NOGIT=1`,
  `-Overrides` EXACTLY = packet `overrides` string (canonical sorted),
  `-CostSourceManifest` relative path, `-AllowResearchCostProxy`.
- Read `run_manifest.json` + `logs/tester_journal_delta.log` SUMMARY
  counters + lifecycle CSV — verify the EXECUTED sample matches the
  declared mechanism (signal count ~probe estimate; filter counters show
  only declared gates).

### Phase 5b — Trade-path autopsy (BEFORE any kill verdict)

Never kill a family on headline PF alone. Reconstruct MAE/MFE for every
executed trade (`tools/autopsy_mae_mfe.py` pattern: lifecycle CSV + M5 bars):
- Winners' median MFE large (>10p) + capture <0.6 -> **management leak**:
  the premise moved price but the exit donated it back. Design exits from
  the excursion data (premise-invalidation cut on no-progress trades,
  BE move at +1R, chandelier trail) -> NEW hypothesis with the autopsy
  declared as post-observation basis. Do NOT re-run the same spec.
- Winners' median MFE ~ 0-2p -> **premise dead**: price never moved for
  us; kill the family for real.
- Losers' MAE >> median stop distance -> stop placement/invalidation leak.
- Counterfactual exits on winners are NOT proof (selection-on-survival);
  they are design input for the next prereg only.
- **GATE C (mandatory on any probe-vs-governed divergence)**: Microstructure
  & Execution + Adversarial Auditor explain the gap BEFORE the verdict is
  written. Divergence unexplained = evidence untrusted, not "bad luck".

### Phase 6 — Verdict + learn

- PASS economics (PF>1.30 x1 etc.) → proceed to OOS/robustness per GOAL;
  still research-proxy, not promotion.
- KILLED → update row: `state:'killed'`, `verdict:'KILLED_AT_MODEL_0'`,
  full `reason` (numbers), `metrics`, `run_ids`; bind
  `validation.source_snapshot_path` + `source_snapshot_sha256` (copy the
  run's `snapshot/source/<EA>.mq5` into
  `03. EA Developer/<EA>/research/source_snapshots/`) when canonical
  source will diverge.
- Append lessons to `04. Memory/hot.md` (new traps, new evidence rules).
- Kill orphan isolate terminals → Phase 1.

---

## KNOWN-TRAP RESPONSE TABLE (self-fix playbook)

| Symptom | Cause | Fix |
|---|---|---|
| HQ ~49-82, gate reject | sentinel `1970` window predates broker coverage | bind `from` to verified coverage from the report; rebuild packet; rerun |
| `data_fingerprint` mismatch post-run | provisional bars/ticks/hq in packet | read actual from `run_manifest.fingerprint_basis`; rebuild packet with actuals; rerun |
| `server_fingerprint` mismatch | liveupdate build bump mid-run | re-run `measure_cost_evidence.py` to refresh `ident`, rebuild, rerun promptly |
| byte-identical results after code/default change | tester `.set` last-used memory replays stale inputs | delete `runtime/.../MQL5/Profiles/Tester/<EA>.set`; pin ALL params via overrides |
| `overrides does not match CLI` | order/format drift | pass CLI `-Overrides` = packet `overrides` verbatim (canonical sorted) |
| `Execution blocked` other fields | registry edited after packet built | rebuild packet LAST, after final registry state |
| Registry `verdict required` / `additional properties` | schema drift on manual row edit | screened rows carry verdict/reason/metrics/validation/updated_at_utc; snapshot fields live INSIDE `validation` |
| `INIT_FAIL bad_input=X` | validation range doesn't accept spec value | widen `BeValidateInputs` bounds to the spec's legal range (0=off conventions) |
| Audit FAIL `unproven_closed_bar_shift` | computed shift expr | refactor CopyRates into `if(shift<1) return`-guarded helper |
| `Required sidecar *_LifecycleTrades_*` absent | EA init failed / run never executed | read journal INIT_FAIL line; fix validation; rerun |
| Compile/run refused: `factory executable running` | orphan isolate terminal | kill `terminal64.exe` under `02. AlphaFactory/runtime/` only |
| Empty attach (0 bars) | fresh terminal no session/history | `symbol_select` + retry loop; or discover via governed run instead |
| `copy_rates_range` = 0 across history | stub .hcc gaps | chunked `copy_rates_from` stepping day-by-day |
| probe PF high, governed PF ~0.1-0.3 | hcc_reader fabricates bars in burst regions (roll/news); probe prices ≠ tradable prices | validate entry/exit prices vs real fills (lifecycle CSV, journal) BEFORE prereg; GATE A mandatory |

## ADVISORY BOARD

Role cards: `.devin/agents/*.md` + routing in `.devin/agents/README.md`.
Invoke via `run_subagent` profile `subagent_explore` (read-only) with the
card text + gate context + ban list pasted into the prompt. Gates are
blocking: a FAIL from any seat halts the phase until resolved or the
Owner overrules. Advisors run in parallel when independent.

## STOP / REPORT conditions

- GOAL gates met on governed evidence → report PASS artifacts; demo stage
  still needs Owner sign-off; live remains blocked.
- All legal direction classes exhausted → report the falsification ledger
  + the binding-constraint analysis (which gate is structurally hardest)
  + concrete amendment options; wait for Owner decision.
- Auth/permission/external-account issue → ask the Owner (last resort
  only — exhaust tooling first).
- After each iteration, output a compact status: hypothesis, run_id,
  headline metrics vs gates, kill-or-continue decision, next direction.

Begin at Phase 0 now.
