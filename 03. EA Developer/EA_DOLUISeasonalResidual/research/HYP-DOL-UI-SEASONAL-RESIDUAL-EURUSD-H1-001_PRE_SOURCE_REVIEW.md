# HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001 - pre-source review

Status: `PASS`

Reviewer scope: read-only re-review of `README.md`, the canonical frozen source
plan, `build_dol_ui_source.py`, and `tests/test_build_dol_ui_source.py`.
Only this review file was updated. No MT5, market-price outcome, economic run,
MQL5 build, paid source, or source attempt was opened.

## Findings

No blocking findings remain.

The prior `BLOCK_SOURCE_IDENTITY_UNBOUND_RAW_CACHE` is closed. The source plan
now freezes 100% in-attempt PDF download from returned official URLs and zero
pre-existing raw-cache reads as an explicit source-only gate
(`HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_SOURCE_FEASIBILITY_PLAN.md:107`).
The builder now scopes raw storage under the exact attempt id
(`build_dol_ui_source.py:77`), rejects a pre-existing attempt raw root
(`build_dol_ui_source.py:487`), rejects any pre-existing per-PDF cache before
download (`build_dol_ui_source.py:337`), and adds
`all_pdfs_downloaded_in_attempt` to the verdict gates
(`build_dol_ui_source.py:517`). The added focused test covers cache rejection
(`tests/test_build_dol_ui_source.py:81`).

## Contract checks

- PIT/source identity is source-only and official-link-bound. The plan permits
  only DOL archive discovery, PDF download, field extraction, hashing,
  source-direction counts, and static tester CSV creation; it forbids EURUSD
  prices, returns, trades, PnL, PF, drawdown, validation/holdout target prices,
  MQL5, MT5, optimization, promotion, paper, and live trading
  (`HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_SOURCE_FEASIBILITY_PLAN.md:15`).
- Archive cutoff and stage gates remain exact: cutoff `2026-08-06`, 441 rows,
  and 260/104/77 source-stage counts (`build_dol_ui_source.py:37`,
  `:38`, `:49`, `:351`).
- Official filename anomaly handling remains correct: path year plus filename
  MMDD defines release date; the two-digit filename suffix is recorded but not
  authoritative for the known 2019 anomaly
  (`HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_SOURCE_FEASIBILITY_PLAN.md:75`,
  `build_dol_ui_source.py:176`, `tests/test_build_dol_ui_source.py:63`).
- Parser failures are fail-closed for missing core fields, PDF/URL date
  mismatch, impossible claims-week lag, and missing revised-prior lineage
  (`build_dol_ui_source.py:260`, `:268`, `:222`, `:295`;
  `tests/test_build_dol_ui_source.py:154`).
- One-shot/path/hash safety is adequate for this pre-source gate: exact attempt
  id is required, the evidence root cannot already exist, packet path must stay
  under workspace, and the run packet hash-binds the plan, script, tests, and
  this review file (`build_dol_ui_source.py:459`, `:462`, `:649`, `:452`).

## Test receipt

Command run with bytecode and pytest cache disabled:

`PYTHONDONTWRITEBYTECODE=1 python -m pytest "03. EA Developer\\EA_DOLUISeasonalResidual\\research\\tests\\test_build_dol_ui_source.py" -q -p no:cacheprovider`

Result: `9 passed in 0.13s`.

## Authorization verdict

The full source-only census is authorized under the frozen packet/attempt
contract. This PASS does not authorize target outcomes, code, economics,
validation, holdout, paper, or live trading. A source PASS may only hand off to
a new, separately frozen economic preregistration as stated in the plan.
