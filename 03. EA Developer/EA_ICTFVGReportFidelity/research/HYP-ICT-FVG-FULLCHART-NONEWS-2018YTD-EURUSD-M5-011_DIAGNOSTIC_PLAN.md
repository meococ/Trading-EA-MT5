# HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011 - 2018-to-present no-news diagnostic

Status: **FROZEN AFTER OWNER REQUEST, BEFORE HYP-011 SOURCE CHANGE OR OUTCOME**

## Parent evidence and purpose

- Parent: terminal diagnostic
  `HYP-ICT-FVG-FULLCHART-MICRORISK-EURUSD-M5-010`.
- Parent source SHA-256:
  `E41BEBC01276BFFE6E844563272AAD08A38BD05AB0674939E4D5D42C84412C2F`.
- Parent completed the 2019-2022 chart at 0.01% micro-risk and no effective
  account-DD stop, but it intentionally kept 2023 onward sealed.
- The Owner now explicitly requests a new observation from 2018 to the current
  date, `2026-07-19`; this authorization opens that date range for this
  diagnostic child only.
- The compiled news ledger covers only 2019-01-01 through 2022-12-31 and
  `NewsBlocked()` rejects every timestamp outside that coverage. Keeping the
  parent news setting would therefore produce no 2018 or 2023+ trades and would
  not answer the Owner's full-chart request.
- Purpose: observe the unchanged high-recall control signal/execution path over
  the available full chart with the news filter consistently disabled. This is
  not a report-fidelity, economic, prop-firm, promotion, paper or live test.

## Frozen legal delta

1. Change only source version/embedded identity to version `1.17` and
   `HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011`. No functional source
   line or strategy threshold may change.
2. Use exactly one preset:
   `presets/EURUSD_M5_CONTROL_FULLCHART_2018YTD_NONEWS.set`, SHA-256
   `1B48AAA7ACBE2C50686A1261D4A3C6CF019C2625DB1654BBD9454B25125B2997`.
3. Relative to the HYP-010 preset, the only input deltas are:
   `InpRequireNewsGuard: true -> false` and
   `InpMagic: 5600720 -> 5600721`.
4. The new magic isolates persistent tester risk state. It is not a strategy
   parameter. News is disabled for every year rather than silently mixing
   guarded 2019-2022 with blocked outer years.
5. Keep `InpRiskPercent=0.01` and `InpMaxAccountDrawdownPct=100.00`; dollar P&L
   and percentage DD remain micro-risk diagnostics only.

## Frozen execution contract

- Run exactly one `CONTROL_FULLCHART_2018YTD_NONEWS` arm through AlphaFactory.
- FivePercent EURUSD M5, MT5 Model 0, `2018.01.01-2026.07.19`, deposit 100,000,
  leverage 1:100, tester-current spread, no optimization and no other override.
- The end date is the exact requested cutoff. The tester may only contain
  closed historical data through its latest available tick; report the actual
  first/last modeled timestamp and never imply future or missing data exists.
- The full-fidelity challenger is excluded because this experiment deliberately
  removes a required report filter and cannot answer challenger fidelity.
- Historical spread/commission/slippage provenance remains failed.
  `promotion_eligible=false` regardless of outcome.

## Required proof and readout

- Before outcome: append registry pre-outcome states, run the identity test red,
  update source identity only, run all package tests, compile 0/0, pass an
  exact-source non-repaint audit, and issue a fresh source/binary receipt.
- Valid completion requires manifest/RunMeta HYP-011 identity agreement, 100%
  tester history quality, no early stop-out, actual modeled timestamps spanning
  the available requested interval, and exact lifecycle entry/final-close
  reconciliation.
- Report first/last trade, yearly trade counts and economics, full-period
  cadence, PF, win rate, normalized expectancy, max DD and RunMeta funnel.
- If the chart completes and reconciles, terminal verdict is
  `DIAGNOSTIC_COMPLETE_2018_YTD_NONEWS`; the killed parent family remains killed.
- If data, identity, receipt, stop-out or accounting fails, verdict is
  `INVALID_DIAGNOSTIC`. No tuning or further rerun is authorized under this ID.
