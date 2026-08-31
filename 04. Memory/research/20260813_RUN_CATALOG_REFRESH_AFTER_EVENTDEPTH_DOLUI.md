# Run-catalog refresh after EventDepth and DOL UI — 2026-08-13

## Operation

- Command: `python "02. AlphaFactory/tools/runs_db.py" build`
- Raw run folders scanned: `627`
- Catalog rows inserted: `504`
- Folders skipped by the catalog parser: `123`
- Parser errors: `0`
- SQLite query after rebuild: `504` rows across `145` exact EA identities.
- Human summary after rebuild: `482` evaluable runs across `128` summarized EA
  names. The difference is parser/evaluability and display grouping, not an
  economic verdict.

## Shelf reconciliation

- Canonical top-level packages with a same-name `.mq5`: `111`.
- A literal package-name versus catalog-identity comparison leaves `33` names
  without an exact catalog identity. This is a discovery set only: aliases,
  collection/harness packages, invalid first attempts, superseded source
  identities and terminal lineages are present.
- The authoritative earlier package audit remains controlling:
  `04. Memory/research/20260813_UNRUN_EA_SHELF_DATABASE_AUDIT.md`.
- Package documentation rechecked in this refresh confirms representative
  cases: `EA_FisherTrendPullback` stopped before baseline for engineering and
  de-dup defects; `EA_FVGConfluence` and `EA_HybridICT_Sonic` are terminal;
  `EA_TickFlowCVDProbe` and `EA_VRAS_QuoteTickAcceptance` are collection-only;
  `EA_DOLUISeasonalResidual` is now correctly indexed and terminal.

## Evidence boundary and verdict

- Catalog PF/net rows were not used to choose a candidate. The SQLite catalog
  is an index; authoritative verdicts stay in package prereg/results and the
  candidate registry.
- Bounded Grok Build review returned `NO_EXISTING_PACKAGE_CANDIDATE`: leave the
  exact-name difference untouched and require either a current nonterminal
  prereg for a genuinely distinct object or a new source/clock. Lead accepts
  that scoped conclusion because it matches the local package authority; Grok
  supplied no execution authority.
- `NO_REVIVAL_CANDIDATE_FROM_EXACT_NAME_DIFF`.
- This is not global infeasibility. It closes the shortcut "no same-name DB row
  means untested edge" and keeps the goal `ACTIVE / UNMET` while requiring a
  materially new information mechanism or a genuinely nonterminal frozen
  package contract before another baseline.
