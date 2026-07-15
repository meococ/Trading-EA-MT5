# EA Session Agent Roster

Canonical role specs for the multi-agent research loop.
Operating contract: `../multi_agent_roster.md`.

## Roles

| Spec | Mode | Default model | Spawn when |
|------|------|---------------|------------|
| [red-team.md](red-team.md) | readonly | `cursor-grok-4.5-high-fast` | prereg freeze, pre-backtest, post-fail |
| [research.md](research.md) | readonly | `cursor-grok-4.5-high-fast` | new idea, failure packet, frontier blocked |
| [impl.md](impl.md) | write (bounded) | `cursor-grok-4.5-high-fast` | probe pass + prereg freeze |
| [qc.md](qc.md) | readonly | `cursor-grok-4.5-high-fast` | post-compile, pre-/post-backtest |
| [coordinator.md](coordinator.md) | merge | session default | always (parent) |

## Spawn checklist (parent)

1. Read role file under this folder; paste mission + I/O into Task prompt.
2. Task tool **must** pass `model: "cursor-grok-4.5-high-fast"` (subs only).
3. Readonly wave: max **2–3** parallel; never full four for a one-line hotfix.
4. Write wave: only `impl` (or parent if `impl` not spawned); MT5 sequential.
5. Merge via [packets/MERGE_MEMO_TEMPLATE.md](packets/MERGE_MEMO_TEMPLATE.md).
6. Session notes: [memory/](memory/README.md).
7. Chốt phiên (proactive): [packets/SESSION_CLOSEOUT_TEMPLATE.md](packets/SESSION_CLOSEOUT_TEMPLATE.md)
   + skill `session-closeout` — coordinator owns A docs / B self-improve merge /
   C cleanup; subs propose-only for standing ops (`AGENTS.md` §6).

## Local Cursor launchers

`.cursor/agents/ea-*.md` (gitignored) point here with frontmatter model pin.
Skills: `.cursor/skills/failure-triage/`, `.cursor/skills/chart-state-probe/`,
`.cursor/skills/session-closeout/` (canonical twin:
`04. Project Control/skills/session-closeout/`).
