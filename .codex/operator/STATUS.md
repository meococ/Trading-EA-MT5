# AlphaFactory Cleanup and Quality Review Status

- Authority: operational recovery ledger only; `04. Memory/hot.md` remains the
  sole canonical live-scope owner.
- Goal: review `02. AlphaFactory/` with a read-only Grok 4.5 review squad,
  remove only proven disposable/stale files, and implement the smallest
  evidence-backed quality hardening slice.
- Acceptance criteria: protected runs and registry-referenced artifacts remain
  intact; every deletion is inventory-backed; source-of-truth validation is
  green; focused tests and `git diff --check` pass; no MT5 backtest/live action;
  no commit/push without explicit Owner authorization.
- Current state: cleanup and hardening slice DONE; full closeout is
  `BLOCKED_BY_MISSING_INPUT` because the declared `G:` backup root is not
  mounted, so 10 `backup-only` entries cannot be verified.
- Latest evidence: 7/7 focused tests pass; dry-run archive protection scans 202
  referenced IDs and 210 effective keep IDs; runs storage fell from
  5,896,008,396 to 5,280,125,523 bytes; cache removal brings total reclaimed to
  616,409,342 bytes. No run folder was archived or deleted.
- Current diagnosis: cleanup automation now defaults dry-run, requires explicit
  EA scope, contains plan output, writes plans atomically, and scans current
  control surfaces plus hot-ledger details. The remaining validator failure is
  external availability, not JSON/Markdown parity or encoding.
- Next experiment: mount the declared Google Drive `G:` root and rerun
  `python 04. Memory/validate_source_of_truth.py`. Only after a reviewed
  off-volume destination exists should the 1.74 GiB Sonic archive dry-run plan
  be considered for `-Execute`.
- Budget: no backtest, no live terminal/order action, no unmanifested evidence
  deletion, no branch/worktree creation, no commit/push.
