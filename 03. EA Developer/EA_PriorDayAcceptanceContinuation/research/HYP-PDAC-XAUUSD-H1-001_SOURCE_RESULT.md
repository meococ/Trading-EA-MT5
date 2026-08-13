# HYP-PDAC-XAUUSD-H1-001 source-feasibility result

Verdict: `PASS_SOURCE_FEASIBILITY`

No outcomes, future prices, returns, costs, PnL, MFE/MAE or profit factor were
opened. This pass authorizes implementation review only.

## Result

- Design rows: `29,461` native FivePercent XAUUSD H1 bars.
- Raw first-acceptance events: `573`.
- Exact-next executable events: `564`; coverage `98.4293%`.
- Cadence: `2.162103/week` over `260.857143` weeks.
- Direction: `312 LONG` (`55.3191%`) / `252 SHORT` (`44.6809%`).
- Year counts: 2018 `122`, 2019 `102`, 2020 `108`, 2021 `104`, 2022 `128`.
- Annual cadence range: `1.9562–2.4548/week`; max-year share `22.6950%`.
- Conflicts: `0`; every frozen source gate passed.

## Bound artifacts

- Source prereg SHA256:
  `1D86DC8DD8A88986CF99682FD93FFA2519C883915FE76056F3D820A2E4CB52D4`.
- Analyzer SHA256:
  `9B1360A2CE2656294703E3AB24FBF08B0E734099AA60ED39D6ECA6FB23B6AFE9`.
- Tests SHA256:
  `5D80F281C678FEAAEA2A50FFA9E45B69C3DF863262C6CC33D150E9546463C265`;
  `4 passed` before the source scan.
- Source report SHA256:
  `786128C72071964F3F2A2010DFEB2BA976E9F1CE4191BE981E9911C342951208`.
- Source ledger SHA256:
  `D17738ED6BAA478A8B2F7BF1788EAAB36B726C93D1AA7BB1DE48FF74BD67045F`.
- Native H1 source SHA256:
  `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`.

No threshold, session, timeframe, direction, cooldown or debounce was changed
after this count.
