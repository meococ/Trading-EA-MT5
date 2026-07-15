# Project Lifecycle FSM for Autonomous EA Delivery

Use this reference to prevent an EA project from drifting into "pretty good, stop here".

## Locked finish line
- Finish line: `PROP_READY`
- Reporting cadence: `milestone only`

## Canonical states
1. `DISCOVERY`
   - research edge, repo, tooling, market structure, pain clusters
2. `BASELINE_LOCKED`
   - baseline run, metrics, equity chart, key weaknesses captured
3. `HYPOTHESIS_QUEUE`
   - ranked backlog of evidence-backed hypotheses
4. `IMPLEMENT_TEST`
   - exactly one meaningful change being implemented/tested
5. `FORENSIC_VALIDATE`
   - report/datalog/equity/regime/WFA/Monte Carlo/sensitivity review
6. `PROMOTION_REVIEW`
   - compare candidate against performance, robustness, pain, and live-safety gates
7. `ARCH_HARDENING`
   - architecture/execution/risk design is now the main blocker
8. `BLOCKED_RESEARCH`
   - evidence gap blocks quality decision; build tools, indicators, or research next
9. `PROP_READY`
   - candidate passes gates and has rollout artifacts

## Transition rules
- `DISCOVERY -> BASELINE_LOCKED`
  - only after a reproducible baseline and weakness summary exist
- `BASELINE_LOCKED -> HYPOTHESIS_QUEUE`
  - only after next 3-10 candidate tasks are ranked
- `HYPOTHESIS_QUEUE -> IMPLEMENT_TEST`
  - choose the single highest-value next change
- `IMPLEMENT_TEST -> FORENSIC_VALIDATE`
  - mandatory; never jump directly to done
- `FORENSIC_VALIDATE -> PROMOTION_REVIEW`
  - only after evidence stack for that run is complete enough
- `PROMOTION_REVIEW -> PROP_READY`
  - only if all gates and delivery artifacts pass
- `PROMOTION_REVIEW -> ARCH_HARDENING`
  - if execution/risk/architecture weaknesses dominate
- `PROMOTION_REVIEW -> BLOCKED_RESEARCH`
  - if evidence is insufficient or 3 rejects in a row reveal a missing research/tooling layer
- `BLOCKED_RESEARCH -> HYPOTHESIS_QUEUE`
  - only after the missing evidence artifact exists
- `ARCH_HARDENING -> IMPLEMENT_TEST`
  - once a specific architecture task is selected and scoped

## Loop engine priority
At each loop, choose the highest blocker in this order:
1. architecture/execution safety blocker
2. largest equity pain cluster
3. robustness gap
4. live-safety gap
5. tooling/evidence gap
6. alpha expansion scenario

## Rejection / escalation rules
- 1 meaningful hypothesis = 1 run
- 3 rejected hypotheses in a row -> stop signal tinkering and enter `BLOCKED_RESEARCH`
- if current candidate is not trusted for real money or a prop challenge -> cannot enter `PROP_READY`
- if the same question keeps recurring without a clean artifact answer -> build the missing tool/indicator/script

## Milestone-only reporting
Report only when one of these happens:
- baseline locked
- strong hypothesis rejection
- candidate beats baseline materially
- architecture phase completes
- candidate reaches `PROP_READY`

## Mandatory status artifact
Every active EA branch should keep a status file containing:
- current lifecycle state
- last transition and reason
- current baseline to beat
- blocker stack in priority order
- next single action
- required evidence still missing

## Phoenix current default interpretation
If Phoenix has a strong baseline but unresolved execution/design blockers, the correct state is:
- `PROMOTION_REVIEW` denied
- current routed state = `ARCH_HARDENING`
