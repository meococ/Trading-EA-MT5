# HYP-PTR-T2-DATA-EPOCH-D0-M5-005 — Model-4 all-history data epoch

## Status and authority

- Frozen before any HYP005 MT5 launch, report, journal, trade, PnL, or economic observation.
- Campaign: `CAMPAIGN-PTR-E01`; generation: `T2`; phase: `P4`.
- Authority: `DATA_ACQUISITION_ONLY_NO_PERFORMANCE`.
- Run role: `control`; telemetry profile: `none`; telemetry tier: `off`.
- This prereg authorizes no trading, performance interpretation, economics, optimization, validation/holdout access, promotion, paper trading, or live trading.
- HYP004 is terminal-invalid under `HYP-PTR-T2-DATA-EPOCH-D0-M5-004_GOVERNANCE_CLOSEOUT.json`. Its one XAUUSD engineering launch is capability evidence only and is not a HYP005 result.

## Immutable identity

- EA: `EA_PTR_T2_DataEpochD0V3`.
- Canonical source: `03. EA Developer/EA_PTR_T2_DataEpochD0V3/EA_PTR_T2_DataEpochD0V3.mq5`.
- Frozen source SHA256: `07EF04835CC7624FC8632A0B6E1958A754A93205FB679751B4748D45E6EA4B29`.
- Data epoch contract: `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH_V3.json`.
- Data epoch SHA256: `AEBB0EC6AEBEBE5D0ECA81FC42CB1765CF67835BA1FC134D12827E7B87C3A43E`.
- Evidence ledger: `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EVIDENCE_V3.jsonl`.
- The source input default and the fail-closed `Configure()` comparison must both equal the frozen V3 epoch SHA above.
- Any source, prereg, epoch, parser, packet, registry, cost-manifest, or expected Tester-mode change requires a fresh hypothesis ID.

## Frozen MT5 contract

- Server: `FivePercentOnline-Real`.
- Tester model: integer `4`.
- Model label: `Every tick based on real ticks`.
- Exact required journal readback: one structured `Tester` component line for the selected symbol and `M5` whose payload is exactly `<SYMBOL>,M5 (<server>): generating based on real ticks`, case-insensitive only for letter case.
- Loose suffixes, fallback wording, a mode line belonging to another symbol/timeframe, `every tick generating`, or `every tick generated from M1 bars` invalidate the run.
- Timeframe: `M5`.
- Requested range: `1970.01.01` through `2026.07.30`; the sentinel requests all broker history available as of `2026-07-30T23:59:59Z`.
- History Quality: strictly greater than `97.0%`; equality at `97.0%` fails.
- Mandatory symbols, exact order, no skip:
  `XAUUSD`, `BTCUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`, `AUDUSD`, `NZDUSD`.
- Required series-proof fields:
  `symbol`, `m5_synchronized`, `m5_first_epoch`, `m5_terminal_first_epoch`,
  `m1_server_first_epoch`, `m1_terminal_first_epoch`, `m5_bars`,
  `terminal_maxbars`, `copytime_from_epoch`, `copytime_count`,
  `copytime_result`, `copytime_first_epoch`, `copytime_last_error`.
- Required equalities: `copytime_from_epoch == m5_first_epoch`,
  `copytime_first_epoch == m5_first_epoch`, terminal M5 first date equals the
  report/journal start date, and terminal M1 first date equals server M1 first
  date.
- Allowed coverage classes: `FULL_2018_PLUS` or `BROKER_LIMITED_START`.
- Rejected coverage class: `INVALID_TRUNCATED_TERMINAL_CACHE`.
- Zero trades is mandatory. PF, win rate, expectancy, Sharpe, drawdown, return,
  cadence and any economic metric are undefined for this collection hypothesis.

## Serial execution and stopping rule

1. Compile and non-repaint/no-trade audit the frozen source.
2. Build nine hash-bound task packets only after the registry screened row and
   campaign `DATA_REPAIR` row bind HYP005 and the V3 epoch.
3. Dry-run the XAUUSD packet through `ea_research_loop.ps1`.
4. Launch XAUUSD first. If identity, source-to-epoch binding, exact Tester mode,
   journal range, D0 series proof, receipt, manifest, or zero-trade checks fail,
   stop all further HYP005 launches and close HYP005 as engineering-invalid.
5. If XAUUSD passes every structural gate, run the remaining eight symbols
   serially in the frozen order. A symbol-level History Quality failure does not
   permit skipping the remaining symbols.
6. Append a selected evidence row only after independently reparsing and
   rehashing the receipt, task packet, manifest, report and journal.
7. `validate_data_epoch.py --require-complete` must pass with nine selected PASS
   rows before the V3 epoch can unlock any later economic hypothesis.

## Falsification and non-rescue

- A structural failure terminates HYP005; fixes use a fresh ID.
- A History Quality result at or below `97.0%` fails that symbol under this exact
  broker/server/Model-4/all-history contract.
- Missing or invalid evidence is `INVALID_REPAIR`, never `no edge`.
- Results from HYP003/HYP004 informed this fresh prereg but cannot be used to
  tune or reinterpret HYP005 after launch.
- Even a 9/9 data-epoch PASS proves only data/execution eligibility. It does not
  prove a strategy edge or authorize trading economics.
