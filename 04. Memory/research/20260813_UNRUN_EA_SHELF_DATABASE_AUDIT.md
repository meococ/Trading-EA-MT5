# Unrun EA shelf database audit

Date: 2026-08-13

Authority: database-first de-dup only. This audit does not authorize a new
hypothesis, backtest, optimization, validation, promotion, paper trading or
live trading.

## Inventory

- Canonical `03. EA Developer` packages containing a top-level `.mq5`: 107.
- AlphaFactory runs database: 499 indexed rows across 143 EA identities, from
  2026-06-21 through 2026-08-12.
- Source packages with no same-name physical AlphaFactory run directory: 16.
- `runs_db.py gates`: 477 evaluable runs and zero all-gate passes.

The 16 no-same-name-run packages are not 16 untested economic candidates:

### Non-strategy/source-only packages (4)

- `EA_ExecutionKernelHarness`: execution compile harness, not a signal.
- `EA_ProspectiveCalendarPIT`: source lane terminal as `KILL_CALENDAR_LANE`.
- `EA_PTR_T2_DataEpochD0`: collection/data-epoch probe, no trading authority.
- `EA_VRAS_QuoteTickAcceptance`: prospective quote plumbing only; historical
  and economic authority closed.

### Exact strategy objects already terminal before a same-name run (5)

- `EA_CBRK_XAUBreakout`: terminal DQ gate failure before baseline; no direct
  rerun authority.
- `EA_FisherTrendPullback`: `STOP_PRE_BASELINE_ENGINEERING_ONLY`; recursive
  state defects and extreme-oscillator/trend adjacency.
- `EA_FVGConfluence`: terminal de-dup kill against the prior FVG continuation
  family.
- `EA_HybridICT_Sonic`: terminal Model-0 lineage, PF 0.98 and about 0.22 trades
  per elapsed week.
- `EA_ICTVisualEdge`: terminal design-window economic kill; extractor retained
  only as a method record.

### Superseded engineering identities (7)

- `EA_MultiAssetTSMOMD1V4` and `EA_MultiAssetTSMOMD1V5` are intermediate source
  identities inherited by V6; the authoritative V6 failure artifact records PF
  0.4853467684, net -USD 7,708.23 and 0/4 positive years.
- `EA_SupertrendBurstScalperTradeV6`, V9, V11 and V12 are consumed governance or
  engineering predecessors. The later sealed V13 run is not a survivor and the
  exact Supertrend lane was abandoned after terminal recovery attempts.
- `EA_SupertrendBurstScalperTradeV14` is an unregistered identity draft that
  reuses the already-consumed HYP027 identity; it cannot create fresh economic
  authority.

## Family-aware registry reconciliation

A second read on 2026-08-13 reconciled append authority by EA family and by
parent/child leaf instead of treating the latest row of each hypothesis ID as
an independent live candidate:

- registry rows: 978;
- unique hypothesis IDs: 390;
- latest rows across 99 EA names: 60 `killed`, 38 `parked`, 1 `screened`;
- graph leaves: 167 total, comprising 102 `killed`, 64 `parked`, and 1
  `screened`.

The single screened leaf, `HYP-PTR-T2-DATA-EPOCH-D0-M5-001`, is not an open
economic object. It is an old collection-only data-epoch receipt superseded in
the same campaign by HYP002 through HYP005; the V3 successor is terminal at its
prelaunch dependency/data-quality boundary. Source-pass parents in Event Depth
Transfer, JCDR, Round Cascade, G10 cross-sectional momentum and triangular lag
are likewise closed by their later descendants.

This corrects the naive per-hypothesis scan that can show stale parent states as
open. Current result: zero open economic hypothesis and zero lawful Model-0 run
from the existing shelf. No price, return, compile, backtest or economic trial
was opened by this reconciliation.

Validation boundary: all 978 JSONL rows parse successfully. The full candidate
registry validator is currently red on pre-existing immutable-snapshot hash
drift and repeated terminal-transition records in older AIRQMB, RSF, JCDR,
STBS and related lineages; this audit did not modify the registry or repair
those unrelated records. The counts above are therefore structural append
reconciliation, not a registry-validator PASS. `validate_source_of_truth.py`
passes with 82 entries and one optional unavailable Google Drive backup warning.

## Verdict

`NO_REVIVAL_CANDIDATE_FROM_UNRUN_SHELF`.

Absence of a same-name run directory is not evidence of an unused market idea.
Starting any of these 16 packages would either run a non-strategy collector,
repeat a terminal object, or detach an intermediate implementation from its
authoritative lineage. The active goal therefore moves to a materially new,
zero-cost prospective database source rather than manufacturing a baseline from
stale code.
