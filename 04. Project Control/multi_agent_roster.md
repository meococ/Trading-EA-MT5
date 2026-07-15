# Multi-Agent Roster + Failure Mindset Loop

Status: **ACTIVE** (Owner approved 2026-07-15)  
Canonical roster and failure-triage contract. Complements `AGENTS.md`,
`research_doctrine.md`, and `agent_ea_research_loop.md` — does not replace
hard rules (prereg, Model 0, no post-hoc rescue).

**Model pin (mandatory):** every roster sub-agent defaults to
`cursor-grok-4.5-high-fast`. Parent/coordinator keeps the session model;
override only when Owner says so per task.

## Purpose

Session-scoped specialist roster + forward/backward failure triage, compatible
with:

- evidence-first (prereg, registry, Model 0, no post-hoc rescue)
- one lane / one writer
- AlphaFactory = sole kernel
- parallel READ, serial WRITE

## Model pin (sub-agents)

| Role | Default model |
|------|----------------|
| `red-team` | `cursor-grok-4.5-high-fast` |
| `research` | `cursor-grok-4.5-high-fast` |
| `impl` | `cursor-grok-4.5-high-fast` |
| `qc` | `cursor-grok-4.5-high-fast` |
| `coordinator` (parent) | session default — **do not** force Grok |

Launch checklist: Task tool always passes `model: "cursor-grok-4.5-high-fast"`
unless Owner overrides.

## A. Failure Mindset Loop

| Step | Insert where |
|------|--------------|
| Triage invalid vs valid | Before Deep Research loop (`agent_ea_research_loop.md` § Failure Triage) |
| Forward chain | After ideation, before prereg |
| Backward chain | After valid gate fail, before failure packet |
| Chart/state probe | Chart-state label contract — no EA patch from glance |
| Re-run EA | Infra rerun or prereg challenger only — no rescue |

See also: `.cursor/skills/failure-triage/SKILL.md`,
`.cursor/skills/chart-state-probe/SKILL.md`.

## B. Session Roster (4 sub + parent)

| ID | Role | Mode | Model | Spawn when |
|----|------|------|-------|------------|
| `red-team` | Theory critique / red-team | readonly | `cursor-grok-4.5-high-fast` | prereg freeze, pre-backtest, post-fail |
| `research` | Full research / ideation | readonly | `cursor-grok-4.5-high-fast` | new idea, failure packet, frontier blocked |
| `impl` | Coding + compile | **write** (bounded) | `cursor-grok-4.5-high-fast` | after probe pass + prereg freeze |
| `qc` | Code review + theory→quant | readonly | `cursor-grok-4.5-high-fast` | post-compile, pre-backtest, post-backtest |
| `coordinator` | Parent PM | merge only | session default | always active |

Parent does **not** write EA code when `impl` is spawned, except small hotfix
or when `impl` is blocked.

**Budget:** max 2–3 parallel readonly subs per wave. Do not spawn all four for
a one-line hotfix. Archive ≠ evidence; empty shelf still fail-closed via
`ea_contract.ps1`.

## C. File layout

```text
04. Project Control/
  multi_agent_roster.md              # this file (canonical)
  skills/session-closeout/           # canonical session closeout + self-improve
  agents/
    README.md                        # index + spawn checklist
    coordinator.md | red-team.md | research.md | impl.md | qc.md
    memory/SESSION_*.md
    packets/TASK_PACKET_TEMPLATE.md | MERGE_MEMO_TEMPLATE.md
           | SESSION_CLOSEOUT_TEMPLATE.md

.cursor/                             # local (gitignored) — thin launchers
  agents/ea-*.md
  skills/failure-triage/ | chart-state-probe/ | session-closeout/
```

Specs under `04. Project Control/agents/` are source of truth.
`.cursor/agents/` are thin pointers with frontmatter model pin.

## D. Merge protocol (parent)

1. Collect receipt: `verdict`, `evidence_paths[]`, `blockers[]`, `confidence`
2. Conflict order: gates > quant > systems > trader intuition
3. One decision: `GO` | `PROBE` | `PARK` | `KILL` | `BLOCKED`
4. Write `MERGE_MEMO` + update `hot.md` if scope changes

## E. Chốt phiên (coordinator-owned, proactive)

After any meaningful research/improvement session, **parent drives closeout
without waiting for Owner to ask.** Three beats (`AGENTS.md` §6):

| Beat | Parent does | Subs do |
|------|-------------|---------|
| **(A) Docs / research** | Update living docs in scope (`hot.md`, INDEX if map changed, doctrine/roster/skills if process changed, receipts, `do_not_repeat` on new kills; GOAL only if Owner decided) | Flag gaps in receipts; **no** unilateral standing-file edits |
| **(B) Self-improve** | Review + merge earned proposals into skill / role spec / lean AGENTS pointer / tool wrapper | Propose only (`impl` may draft in packet); coordinator merges |
| **(C) Artifact cleanup** | Inventory → keep cited → archive/delete per `run_data_policy.md` | Flag clutter; execute only if coordinator packet grants it |

**Standing ops files (propose → parent merge only):** `AGENTS.md`, `CLAUDE.md`,
`INDEX.md`, `hot.md`, `multi_agent_roster.md`, `agents/<role>.md`, standing
skill rules under `skills/` / `.cursor/skills/`. **Write-scope exception:**
`impl` may edit packet-scoped EA/code under `03. EA Developer/` (and
AlphaFactory compile paths in packet) — not standing ops.

Promote self-improve only with evidence (repeated friction / failed call /
better procedure). Detail → skill/doc; AGENTS stays lean. Sub model pin:
`cursor-grok-4.5-high-fast`.

Checklist / template: `04. Project Control/skills/session-closeout/`
(+ local twin `.cursor/skills/session-closeout/`);
`agents/packets/SESSION_CLOSEOUT_TEMPLATE.md`.
