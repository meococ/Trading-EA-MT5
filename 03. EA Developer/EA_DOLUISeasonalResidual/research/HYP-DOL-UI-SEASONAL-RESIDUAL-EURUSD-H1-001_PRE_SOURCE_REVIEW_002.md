# HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001 - pre-source review 002

Status: `PASS`

Reviewer scope: read-only review of the frozen revision-001 builder,
`HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_SOURCE_REVISION_002.md`,
`build_dol_ui_source_v2.py`, `tests/test_build_dol_ui_source_v2.py`, and the
failed attempt-001 terminal receipts. Only this review file was written. No
MT5, market-price outcome, economic run, MQL5 build, paid source, or source
attempt was opened.

## Findings

No blocking findings remain.

Revision 002 is bounded to outcome-blind parser/source-availability corrections.
The revision note freezes the failed attempt-001 state as all 441 official PDFs
downloaded before ledger/verdict/outcome/economics, then opens exactly one
replacement attempt, `DOLUI001-SOURCE-002`, inheriting the original source
identity, formula, polarity, cutoff, corpus, stage labels, cost limit, and
prohibitions (`HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_SOURCE_REVISION_002.md:5`,
`:10`, `:12`, `:14`). The terminal receipt for attempt 001 is source-only and
failed on `missing core PDF fields: expected`, with `outcome_prices_authorized`
and `paid_requests_authorized` false in `attempt_started.json`.

## Contract checks

- The exact two missing expected-change URLs are frozen and retained without a
  fabricated residual. The wrapper allows missing expected change only for
  `https://oui.doleta.gov/press/2020/090320.pdf` and
  `https://oui.doleta.gov/press/2020/091020.pdf`, records
  `source_availability=EXPECTED_NOT_PUBLISHED`, sets expected change and
  residual to null, and forces `direction=FLAT`
  (`build_dol_ui_source_v2.py:38`, `:112`, `:128`, `:206`).
- Source drift fails closed: a missing expected field at any other URL fails,
  and an expected field appearing at either frozen exception URL also fails
  (`build_dol_ui_source_v2.py:112`, `:114`;
  `tests/test_build_dol_ui_source_v2.py:76`, `:82`).
- Revision lineage is scoped to the initial-claims paragraph before the first
  initial-claims `4-week moving average`; later insured-unemployment revisions
  cannot leak into the field (`build_dol_ui_source_v2.py:141`,
  `tests/test_build_dol_ui_source_v2.py:105`).
- All 441 PDFs must be freshly downloaded under attempt 002. The wrapper changes
  `ATTEMPT_ID`, `EVIDENCE_REL`, and `RAW_REL` to `DOLUI001-SOURCE-002`; the
  frozen core rejects an existing raw root/cache and adds
  `all_pdfs_downloaded_in_attempt` to verdict gates
  (`build_dol_ui_source_v2.py:53`, `:59`, `:63`;
  `build_dol_ui_source.py:337`, `:487`, `:517`).
- Wrapper monkeypatch and run-packet binding are complete for this gate. The v2
  packet schema is distinct and hash-binds the revision plan, v2 wrapper, v2
  tests, this review file, and the frozen v1 core (`build_dol_ui_source_v2.py:217`,
  `:220`, `:237`). Default execution remains inert through the frozen core CLI.
- Source-only authority remains intact: the original README and source plan
  still state no `.mq5`, MT5 run, price outcome, economic verdict,
  optimization, promotion, paper, or live authority
  (`README.md:6`; `HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_SOURCE_FEASIBILITY_PLAN.md:15`).

## Verification

- Combined tests, run with bytecode and pytest cache disabled:

  `PYTHONDONTWRITEBYTECODE=1 python -m pytest "03. EA Developer\\EA_DOLUISeasonalResidual\\research\\tests\\test_build_dol_ui_source.py" "03. EA Developer\\EA_DOLUISeasonalResidual\\research\\tests\\test_build_dol_ui_source_v2.py" -q -p no:cacheprovider`

  Result: `17 passed in 0.15s`.

- Read-only failed-raw corpus probe using the v2 parser over attempt 001 raw
  PDFs:

  `rows=441`; year counts `52/51/53/52/52/52/52/46/31`;
  availability `SIGNAL_USABLE=439`, `EXPECTED_NOT_PUBLISHED=2`; missing URLs
  exactly `2020/090320.pdf` and `2020/091020.pdf`; both missing rows have
  `direction=FLAT`, `seasonal_expected_change=null`, `seasonal_residual=null`;
  all v2 source gates passed.

## Authorization verdict

The replacement full source-only census `DOLUI001-SOURCE-002` is authorized
under the frozen packet/attempt contract. This PASS does not authorize target
outcomes, code, economics, validation, holdout, paper, or live trading. A source
PASS may only hand off to a new, separately frozen economic preregistration.
