# SESSION memory

English notes only (research/evidence language).

## Naming

```text
SESSION_<YYYYMMDD>_<role_or_topic>.md
```

Examples: `SESSION_20260715_redteam.md`, `SESSION_20260715_atrtrail_qc.md`.

## What belongs here

- Role-local working memory for **this session**: open questions, critique
  themes, probe notes, blockers seen.
- Pointers to hash-bound artifacts (paths + SHA when known).

## What does not

- Living project truth → `hot.md`
- Registry / prereg / readout → research ledger (or archive paths)
- Secrets, deal dumps, large logs
- Claims of PF/promote without linked evidence

## Lifecycle

1. Coordinator or role creates a file at session start if useful.
2. Append short dated bullets; do not rewrite history.
3. After closeout, leave in place; do not delete without Owner archive plan.
4. Next session: read `hot.md` first; treat old SESSION files as hints only.

`.gitkeep` keeps the empty folder in git when no SESSION files exist yet.
