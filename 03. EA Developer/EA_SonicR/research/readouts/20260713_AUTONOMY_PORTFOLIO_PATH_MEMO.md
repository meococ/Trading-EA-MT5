# Autonomy Portfolio-Path Coordinator Memo

Date: 2026-07-13  
Coordinator: Cursor Grok 4.5 (read-only intake → English memo only)  
Status: `PHASE 0 OPEN FOR CONTRACT WORK / PHASE 1+ BLOCKED / NO CLEARANCE`  
Authority basis: `hot.md` active truth; `20260711_CODEX_EXECUTION_PLAN_V2.md`;
drafts `HYP-PORTFOLIO-COMPOSE-001` and `HYP-SB-WEEKEND-FLAT-001`; Phase 0
preflight JSONs; `20260710_EA_FAILURE_PORTFOLIO_AUDIT.md`; portfolio-sleeve
gates in `sonic_validation_gates.md`.

## Verdict

Portfolio composition is a legal **parallel governance path** under Owner Phase 0
approval. It is **not** a shortcut past new-strategy discovery (V6/V7 frontier
stops remain binding for any V8). Phase 1+, sleeve selection, outcome screens,
compile, and backtest remain blocked until Phase 0 clearance is earned under a
clean freeze review.

Machine status (pinned):

- Spec: `preflight/20260711_PHASE0_ARTIFACT_SUFFICIENCY_SPEC_V1.json`
- Report: `preflight/20260711_PHASE0_ARTIFACT_SUFFICIENCY_V1.json` → overall
  `BLOCKED`
- Contamination: `preflight/20260711_PHASE0_COORDINATION_CONTAMINATION_ATTESTATION_V1.json`
  → `BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW`
- PROBE_A (`HYP-PORTFOLIO-COMPOSE-001`): `BLOCKED_PROBE_A_EXACT_UNIVERSE_NOT_FROZEN`
  with `candidate_runs: []`
- PROBE_B (`HYP-SB-WEEKEND-FLAT-001`): identity manifests PASS; seven required
  hash bindings missing

---

## 1) Exact missing fields to freeze the portfolio universe WITHOUT outcome mining

The draft prereg already forbids PF/net/cadence ranking. Freeze requires one
canonical, bytewise-sorted inventory with these **non-outcome** fields filled for
every member, then a single `universe_sha256`. Today the exact list is empty and
all of the following are unset:

### Per-member identity inventory (required, currently unset)

| Field | Freeze requirement |
|---|---|
| `universe_member_id` | Stable `<ea_name>/<run_id>` |
| `run_root` | Exact repo-relative active run path under `02. AlphaFactory/runs/` |
| `ea_name`, `run_id` | Directory identity + manifest/config identity check |
| `canonical_main_file` | Exact active repo-local `.mq5` entrypoint |
| `source_sha256`, `compiled_sha256`, `config_sha256`, `report_sha256` | Identity hashes; missing must be explicit, not invented |
| `trade_series_path_sha256` | Path + hash of closed-position/lifecycle series **without row values** |
| `equity_series_path_sha256` | Path + hash of common-calendar equity/return series **without row values** |
| `cost_artifact_path_sha256` | Verified cost artifact + raw provenance path/hash, or explicit missing |
| `symbol`, `suffix`, `timeframe`, `model`, `from`, `to` | Declared configuration identity only |
| `broker_server_account_currency_fingerprint` | Hash/fingerprint only |
| `duplicate_group` | Structural duplicate/collision group from identity hashes only |
| `structural_status` | `eligible` / `alias` / `invalid` with a **non-performance** reason |

### Universe freeze envelope (required, currently unset)

- Canonical sorted serialization of the inventory
- `universe_sha256` over that serialization
- Inventory cutoff timestamp (UTC)
- Worktree/source snapshot binding (no-Git workspace: deterministic path/hash
  snapshot, not Git HEAD)
- Explicit excluded roots (archive/progress/control namespaces)
- Outcome-independent alias rule if duplicates exist (lexicographically
  smallest `(ea_name, run_id)` unless another rule is frozen first)
- If multiple nonduplicate variants remain in one EA/family: either keep **all**
  as a declared tried family, or choose one by a prospectively frozen
  **identity-only** rule — never “best run”

### Prospective composition placeholders that must also be frozen before any
future Phase 1 outcome plan (still `UNSET`; not Phase 0 outcome work)

- Exact allowed combination list / family size
- Weight / risk-normalization / rebalance rule
- Common calendar, timezone, missing-return, and non-overlap rule
- Daily P&L correlation and trade-overlap definitions
- Train and untouched holdout windows
- Cost aggregation and x1 / x1.5 / x2 rules
- Combined exposure, cadence, concentration, and Monte Carlo risk gates
- Multiple-testing correction for every tried combination
- Run budget (currently authorized: `0` outcome screens, `0` compiles,
  `0` backtests)

Phase 0 sufficiency matrix may record only `present` / `missing` /
`malformed` / `identity-mismatch` / `not-applicable` plus paths, hashes,
headers, and reasons. **No performance values.**

Until the inventory is non-empty (or an explicit Owner-frozen empty-universe
blocker is accepted as terminal for this draft) and `universe_sha256` is bound
into the Phase 0 spec, PROBE_A correctly remains
`BLOCKED_PROBE_A_EXACT_UNIVERSE_NOT_FROZEN`.

---

## 2) Can weekend-flat A1 proceed as identity/contract work only?

**Yes — and only as that.**

`HYP-SB-WEEKEND-FLAT-001` is A1: one management intervention (force flat before
broker weekend closure). Phase 0 already allows path/hash/header/identity
inspection and runner source-contract work. It does **not** allow EA source
edits, compile, Strategy Tester, outcome reads, or threshold mining.

Current PROBE_B evidence:

- Identity manifests PASS for nominated donor
  `EA_SilverBullet/20260628_131343` (USDJPY M15 Model 0)
- Trade CSV header + SHA256 PASS
- Still **BLOCKED** on seven missing hash-bound contracts:
  1. `price_path_manifest` (`preflight/price_path_manifest.json`)
  2. side-aware bid path (`preflight/bid_price_path.csv` + `bid_path_sha256`)
  3. side-aware ask path (`preflight/ask_price_path.csv` + `ask_path_sha256`)
  4. timezone contract (`preflight/timezone_contract.json`)
  5. session/holiday weekend-boundary contract (`preflight/session_contract.json`)
  6. symbol contract (`preflight/symbol_contract.json`)
  7. research cost provenance (`preflight/research_cost_provenance.json`)

A1 identity/contract work may therefore continue by **supplying and hash-binding
those seven artifacts without opening trade-result rows**. A2 max-hold remains
unregistered. Combined A1+A2 is a separate future prereg, not a post-hoc join.
Clearance still requires a **clean independent freeze review** because the
coordination session is contaminated by accidental `RunMeta` display
(`outcome_values_used=false`, but freeze review of this session is invalid).

---

## 3) Is any near-miss book (SilverBullet cadence + LondonNY sparse PF) legally
composable under doctrine?

**Still blocked as a confirmatory / portfolio-sleeve composition.**

The 2026-07-10 failure audit is outcome-contaminated reachability evidence:

- SilverBullet near-boundary cadence (~1.99 trades/week) with PF ~1.33 and
  overnight/weekend exposure violations
- LondonNY strong PF / cost-stress quality but ~0.3 trades/week sparsity
- Audit population: 64 runs PF>1.30 all miss cadence; 15 runs in 2–5/week all
  have PF≤1.30; **0** meet both

Doctrine and V2 explicitly withdraw V1’s “PF > 1.30” and “per-EA best run”
eligibility rules. Gates for `portfolio-sleeve` require **at least two
independently confirmed component IDs**, plus hash-bound correlation/exposure
and overlap audits. Neither SilverBullet nor LondonNY is `confirmed`. Neither
is in a frozen outcome-blind universe. Selecting them because one has cadence
and the other has PF is exactly the forbidden post-hoc book construction.

Legal status of that pairing today:

| Claim | Status |
|---|---|
| Historical near-miss narrative / failure taxonomy | Allowed as **exploratory reachability** context only |
| Exact-universe membership via identity-only rules | Allowed only if those runs survive a **new** outcome-blind inventory without PF/cadence selection |
| Portfolio outcome screen / sleeve confirmation | **Blocked** |
| Untouched holdout portfolio verdict | **Impossible** from the audit-selected list |

Any later analysis that intentionally inherits the audit’s outcome-selected
near-misses must stay labeled exploratory and cannot open Phase 1 clearance.

---

## 4) Hard do-not-do list

1. Do **not** treat Phase 0 drafts or `idea/pending` registry rows as execution
   authority, frozen preregs, or strategy evidence.
2. Do **not** read, rank by, or invent membership from PF, net, cadence,
   drawdown, validation PASS, year/session subgroups, or “best run.”
3. Do **not** compose a SilverBullet + LondonNY (or any) book from the
   2026-07-10 audit outcomes and call it a prospective portfolio test.
4. Do **not** run unrestricted “any combination” searches without a frozen
   combination family and multiple-testing correction.
5. Do **not** open trade-result rows, equity points, RunMeta summaries, or
   enhanced_summary metrics during Phase 0 sufficiency work.
6. Do **not** edit, move, rename, or quarantine EA source/includes; do **not**
   compile; do **not** start Strategy Tester / MT5 for this lane.
7. Do **not** merge A1 weekend-flat with A2 max-hold under one ID, or reuse A1
   results as A2 evidence.
8. Do **not** clear Phase 0 using the contaminated coordination session; a new
   versioned spec/attestation and independent freeze review are mandatory.
9. Do **not** interpret missing/zero cost, spread, commission, swap, fee, or
   slippage fields as free execution.
10. Do **not** auto-launch Deep Research V8, registry appends, probes, or EA
    builds from V6/V7 frontier stops without an Owner-approved external
    data-contract change.
11. Do **not** promote, rescue, or threshold-tune shelf near-misses
    (SilverBullet overnight/weekend exposure, LondonNY sparsity, Sonic regime
    pockets) from current fields.

---

## 5) One recommended next executable step (Owner autonomy)

**Do now (no compile / no backtest):** freeze an outcome-blind portfolio
universe packet and re-pin Phase 0 PROBE_A.

Concrete executable action:

1. Enumerate active `02. AlphaFactory/runs/<EA>/<run_id>` members using only
   path existence, identity manifests, and hash fields listed in §1.
2. Apply structural include/exclude/duplicate/alias rules **without opening
   outcome files**.
3. Serialize the sorted inventory, compute `universe_sha256`, record UTC cutoff
   + workspace snapshot hashes.
4. Update
   `preflight/20260711_PHASE0_ARTIFACT_SUFFICIENCY_SPEC_V1.json` (new versioned
   file) so PROBE_A `candidate_runs` is either that exact list or remains an
   explicit empty list with a written Owner terminal-blocker decision.
5. Re-run the Phase 0 artifact-sufficiency producer; expect either continued
   fail-closed blockers or progress toward `READY_FOR_PREREG_FREEZE` — still
   **not** Phase 1.

**Parallel, same authorization class:** create the seven missing SilverBullet
hash-bound preflight contracts for A1 (§2) without reading trade rows.

**Worth-adding later (needs Owner):** independent clean freeze review session
after both PROBE_A universe freeze and PROBE_B contract bindings exist.

**Needs-Owner / not autonomous:** any Phase 1 outcome probe, EA weekend-flat
implementation, compile, Model 0 control/challenger, portfolio correlation
screen, or V8 research reopen.

---

## Parallel-path note vs new strategy V8

| Lane | Current legal state | Role toward GOAL |
|---|---|---|
| `fx_portfolio_silverbullet` Phase 0 | Contract/governance only; clearance blocked | Parallel path: may eventually test composition **if** universe + A1 contracts freeze cleanly |
| New-strategy discovery V6/V7 | `NO_LEGAL_CANDIDATE` / frontier stop | Not a free V8; reopen only after Owner data-contract expansion |
| Cross-sectional USD-factor idea | Cost-data blocked | Not portfolio clearance; separate blocked probe |

Autonomy may push **Phase 0 contract closure** on the portfolio lane. Autonomy
may **not** declare a near-miss book, skip confirmed-component gates, or treat
portfolio composition as a substitute for a legal new EA candidate.

---

## Controlling status (honest)

`DRAFT / NOT FROZEN / OUTCOME ACCESS FORBIDDEN`  
`PHASE 0 IMPLEMENTATION COMPLETE / CLEARANCE BLOCKED`  
`PHASE 1+ BLOCKED UNTIL PHASE 0 CLEARANCE + OWNER PHASE 1 APPROVAL`

No strategy verdict, sleeve confirmation, or GOAL-pass claim is authorized by
this memo.
