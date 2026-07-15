# Codex Execution Plan V1 — FX Portfolio Lane

Date: 2026-07-11
Author: Claude (coordinator). Executor: Codex.
Status: awaiting Owner "go".

This plan supersedes the Codex roadmap draft of 2026-07-11. It bakes in the
four panel-confirmed blockers, the Owner's updated GOAL exposure target
(limit overnight, ZERO weekend crossing), and the discovery-before-ceremony
operating principle. Panel evidence: multi-critic review 2026-07-11 (all
critical/high findings CONFIRMED against repo at line level).

## Non-negotiable corrections vs the original roadmap

1. `alpha.ps1 backtest EA_SilverBullet` throws today at
   `Resolve-TelemetryTierOverrides` (alpha.ps1:1014 -> 206-212) for every
   tier: 9 Sonic telemetry inputs are absent from SilverBullet. A Model 0
   baseline as "first step, no hooks" is dead on arrival. Engineering must
   precede the baseline; the throw itself is the red test that authorizes
   framework work.
2. Per-loop verified cost artifacts are impossible until SilverBullet emits
   `sonic_telemetry.v3` (only emitter today: Sonic's SNR_Telemetry.mqh).
   MetaQuotes friction in donor data is ~0 (commission 0, slippage 0), so
   x1.5/x2 on telemetry-derived cost is a fake pass. Research-screen cost
   numbers MUST come from `tools/sonic_cost_stress.py` with preregistered
   explicit constants, labeled research-only.
3. Hypothesis A ("close all before rollover, overnight=0") is dead under its
   own gates AND under the new GOAL: overnight cohort is the GOOD half of
   the donor book (118 trades, PF 1.548, ~48% of net; weekend = 3 trades,
   net -142.91; swap total -16.90/5y). Replace with A-prime below.
4. Promotion producers (optimization-aware WFA, aligned PBO/WRC) do not
   exist; confirmed stage is structurally BLOCKED. DEFERRED until a real
   challenger needs them. Do not build tooling for stages nothing reaches.

## Phase 0 — Formal scope pivot (coordinator, doc-only, one commit)

- `hot.md` Active Truth: open lane `fx_portfolio_silverbullet` (research
  scope), add unsuffixed `USDJPY` to canonical symbols, keep `EA_SonicR`
  research-only. No run before this edit lands.
- Registry: append two rows, state `idea`, before any outcome is read:
  - `HYP-SB-WEEKEND-FLAT-MAXHOLD-001` (A-prime)
  - `HYP-PORTFOLIO-COMPOSE-001` (composition screen)
- Pin the SilverBullet main file (explicit main-file assertion for
  `EA_SilverBullet_v2.mq5`; quarantine `EA_SilverBullet_v2_Index.mq5` out of
  the EA directory).

## Phase 1 — Two offline probes, in parallel (Codex; Python only; no MT5,
no EA code, no compile)

### Probe B — A-prime donor replay (HYP-SB-WEEKEND-FLAT-MAXHOLD-001)

Hypothesis A-prime: "Force-flat before the weekend, and cap holding time at
H = 30 hours, preserves PF while eliminating weekend exposure and bounding
overnight risk" — matches the new GOAL exposure row exactly.

- Donor: `02. AlphaFactory/runs/EA_SilverBullet/20260628_131343` trades CSV
  (old schema is sufficient; swap column present).
- Frozen params: H = 30h exactly (ONE value — scanning H is banned mining);
  weekend cutoff = last M15 close before Friday session end, server clock.
- Mark-to-market truncated exits on M15 closed bids; include freed-slot
  cadence recovery (source line 714 blocks entries while a position is
  open) as a REPORTED estimate, separately from the conservative
  no-recovery number.
- Preregistered kill gates (read only after freeze): replayed PF < 1.30 at
  declared research cost constants, or per-year cadence materially below
  control (>10% worse in any year), or weekend exposure not zero -> KILL.
- Deliverable: prereg + readout + registry transition (idea -> probe ->
  kill/continue).

### Probe A — Portfolio composition screen (HYP-PORTFOLIO-COMPOSE-001)

Question: is the GOAL corner (PF > 1.30 AND 2-5 trades/week) reachable by
COMBINING existing sparse high-PF sleeves, given none of 217 runs reaches
it alone (64 runs PF > 1.30 all < 2/wk; 15 in-band runs all PF <= 1.30)?

- Inputs: existing run artifacts only (`02. AlphaFactory/runs/`), inheriting
  every caveat of the 20260710 audit (no cost proof on 176/217, favorable
  windows). Output is research-screen ONLY: it answers reachability, it
  does not certify any sleeve.
- Freeze BEFORE reading combined outcomes: sleeve eligibility criteria
  (identity-valid, >= 3 elapsed years, PF > 1.30, per-EA best run only, no
  duplicates per audit), equal-risk weighting, overlap/correlation method
  (daily P&L correlation + same-day trade overlap), combined kill gates
  (combined PF > 1.30 at declared research cost floor, combined cadence in
  2-5/wk, pairwise correlation < 0.5, no sleeve > 60% of trades).
- Deliverable: prereg + readout + verdict: does ANY eligible combination
  clear the corner? If none does with these relaxed inputs, that is strong
  evidence the corner is empty in the current search space -> escalate to
  Owner as a strategic finding (not a defeat verdict; it redirects search).

## Phase 2 — Engineering milestone (Codex; ONLY if Probe B survives)

- Generalize the runner telemetry/sidecar contract per-EA (red test: the
  Phase-1-documented backtest throw). Add pytest coverage under `tests/`.
- Port `sonic_telemetry.v3` into SilverBullet as a NEW repo-local include
  (`03. EA Developer/EA_SilverBullet/Include/SB2_Telemetry.mqh`);
  do NOT edit the shared terminal `ExecQualityLog.mqh`. Vendor the other
  terminal-only includes into the repo for git history.
- Equivalence proof: instrumented build reproduces the donor trade list
  identically (same 520 entries/exits) vs a hookless compile; registered as
  infrastructure (Engineering Safety precedent), not a strategy hypothesis.
- Freeze control config: USDJPY M15 Model 0, window 2019.01.01-2025.12.31
  (84 months — pay the falsification cost once), Deposit=100000,
  Leverage=100, explicit Spread setting, full fingerprint set, preregistered
  drift tolerance vs donor (donor = directional reference only).

## Phase 3 — Matched Model 0 control/challenger (Codex runs, coordinator
reviews verdict)

- Challenger diff: weekend-flat + 30h hold cap ONLY. Exit check placed
  immediately after the new-bar gate and BEFORE all day/holiday filters
  (lines 450/490/491 ordering trap), `server_time >= cutoff` semantics,
  Friday-specific earlier cutoff, cutoff clear of the rollover
  spread-blowout window. Reuse `CloseAllPositions()` (line 991).
- Gates (relative to matched control, guardband <= pass gates):
  - weekend exposure = 0; overnight bounded by the 30h cap;
  - PF >= control PF - 0.03 AND PF > 1.30;
  - per-split cadence >= 0.9x control same split, absolute band 2-5/wk as
    outer bound;
  - research cost stress via sonic_cost_stress.py preregistered constants:
    x1.5 PF >= 1.25, x2 PF >= 1.00;
  - outlier gates: top-5% net share <= control's 89.2% (must not worsen),
    single-trade share <= 10%.
- Family prior gate: the preserved The5ers transfer KILL (PF 1.019, cost
  x1.5 0.9988, 785 trades) is a venue-transfer prior that same-feed stress
  cannot measure. A research-screen pass therefore yields
  "park pending venue-grade cost evidence" — NOT auto-continue to sleeve 2.
- Stop rules: two consecutive same-failure-mode hypotheses close the
  family; no gate edits after seeing numbers; every post-hoc observation
  becomes a new idea.

## Phase 4 — Cost/venue lane (parallel, non-blocking; Codex read-only)

- Monthly `copy_ticks_range` probe for EURUSD/GBPUSD/USDJPY on the current
  terminal; report tick-archive coverage.
- Evaluate one research venue with reproducible tick + commission data.
  Any venue switch for HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001 requires a
  formal dated prereg amendment BEFORE outcome reads, with ticks +
  commission + slippage reference all from that single venue; a tick
  archive alone does NOT unblock outcome reads (slippage leg needs 100 real
  fills under Owner-approved forward micro-risk — out of scope here).

## Deferred (explicitly)

- Promotion-eligible WFA/PBO/WRC producers — build when a challenger
  actually reaches the confirmed gate (contracts already specified in
  `unified_validation.py`).
- USD-factor outcome reads — remain cost-blocked per prereg.
- Any second-sleeve work — Phase 5 of the old roadmap was mis-scoped: the
  USD-factor prereg is a 3-pair router INCLUDING USDJPY, not an
  "EURUSD or GBPUSD" sleeve; overlap with sleeve 1 is a portfolio-stage
  audit, and any true single-pair sleeve is a brand-new hypothesis.

## Division of labor

- Coordinator (Claude): Phase 0 doc edits, prereg review/freeze, verdict
  review at every kill/continue point, registry integrity, Owner
  escalations.
- Codex: probe scripts, readouts, engineering diffs, runs, per-loop
  artifacts; one code diff per loop; commit at every task end (auto-push
  after green gates once a remote exists).
- Critic panel (Sonnet high, fork_context=false): review prereg drafts of
  Phase 1 before freeze; review the Phase 2 equivalence proof; review the
  Phase 3 readout before verdict.
