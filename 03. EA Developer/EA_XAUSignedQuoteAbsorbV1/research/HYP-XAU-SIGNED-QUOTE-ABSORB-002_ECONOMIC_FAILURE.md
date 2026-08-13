# HYP-XAU-SIGNED-QUOTE-ABSORB-002 — Terminal economic failure

## Verdict

`KILL_DESIGN_NO_POSITIVE_EXPECTANCY`. This hypothesis is engineering-valid and source-valid, but economically invalid. It is not promotion-ready and must not be rescued through inversion, session/direction filtering, threshold changes, SL/TP changes, or position sizing.

## Accepted source gate

- Source EA/run: `EA_XAUSignedQuoteAbsorbSourceV3 / 20260812_042943`
- Data: `AFD_XAUUSD_DUKA_V3`, M1, MT5 Model 4 real ticks, `2018.01.01 <= t < 2022.01.01`
- History quality: 100%; data-quality coverage: `FULL_2018_PLUS`
- Ticks: 181,430,829; invalid quotes: 0; reverse-time ticks: 0
- Signals: 32,636; long 15,903; short 16,733; median absolute pressure 11
- Minute coverage: 99.755196%

## Economic baseline

- EA/run: `EA_XAUSignedQuoteAbsorbV1 / 20260812_043613`
- Frozen before economics: risk 0.20% balance, one position, native Bid/Ask spread, SL clamp(1.70 ATR, USD 0.35, USD 1.60), TP 1.25R, seven-minute time exit.
- Trades: 5,193
- Net: -USD 9,825.34 from USD 10,000
- Profit factor: 0.3435489
- Win rate: 26.4%
- Max drawdown: 98.2497%
- Expectancy: -USD 1.89/trade
- Exits: 2,939 SL, 568 TP, 1,686 expert time exits
- Execution errors: zero order-check rejects, zero send rejects, zero close rejects
- Session PF: Asia 0.28, Europe 0.31, New York 0.43

The 26,037 volume rejects occur after the account is depleted below minimum tradable volume and are a consequence, not the cause, of failure. The equity curve is nearly monotonic downward and never presents a credible recovery phase.

## Evidence

- Run manifest: `02. AlphaFactory/runs/EA_XAUSignedQuoteAbsorbV1/20260812_043613/run_manifest.json`
- Report: `02. AlphaFactory/runs/EA_XAUSignedQuoteAbsorbV1/20260812_043613/report.html`
- Bounded journal: `02. AlphaFactory/runs/EA_XAUSignedQuoteAbsorbV1/20260812_043613/logs/tester_journal_delta.log`
- Chart: `02. AlphaFactory/runs/EA_XAUSignedQuoteAbsorbV1/20260812_043613/analysis/analysis_charts.png`
- Analysis: `02. AlphaFactory/runs/EA_XAUSignedQuoteAbsorbV1/20260812_043613/analysis/enhanced_summary.json`

Validation 2022–2023 and holdout 2024–2026-07-31 were not opened.

