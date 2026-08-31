# EA_MZMS_Scalper

Owner-authorized multi-mode M5 research package for MZMS closed-bar
hypotheses on EURUSD/XAUUSD.

## Modes

| `InpSignalMode` | Hypothesis | Magic | Mechanism |
|---:|---|---:|---|
| 0 | `HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006` (legacy control) | 5600722 | EMA200 side control |
| 1 | `HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006` (legacy challenger) | 5600722 | MACD hist local extremum |
| 2 | `HYP-MZMS-XAU-M5-007` | 5600727 | Donchian fresh-impulse initiation |
| 3 | `HYP-MZMS-XAU-M5-008` | 5600728 | EMA20/100 pullback pivot reclaim |
| 4 | `HYP-MZMS-XAU-M5-009` | 5600729 | Bollinger/ATR squeeze breakout |
| 5 | `HYP-MZMS-XAU-M5-010` | 5600730 | RSI/wick/ADX-roll exhaustion fade |

`InpHypothesisId` and `InpMagic` are fail-closed against the selected mode.
Mismatch → `INIT_PARAMETERS_INCORRECT`.

## Shared shell (frozen for 007..010)

- 100% closed-bar signal path (`shift >= 1`); new-bar gate only via `iTime(M5,0)`.
- Risk 0.01% equity; stop = farther of 5-bar structure + 40 XAU points or 1.5×ATR14.
- Target 1.6R; max hold 15 M5 bars; cooldown 5 bars; max 5 entries/UTC day.
- Session 08:00–17:00 UTC (FivePercent EU-DST clock); hard flatten 18:15 UTC.
- Spread ceiling 35 XAU points; BE / partials / trailing OFF.
- XAU campaign presets set `InpRequireNewsGuard=false` (calendar not PIT-complete for XAU).

## Telemetry

- Lifecycle-v3: `${Symbol}_LifecycleTrades_${run_id}.csv`
- RunMeta: `${Symbol}_RunMeta_${run_id}.json`
- Decision-time accepted-entry state:
  `${Symbol}_StateTelemetry_${run_id}.csv`
  (mode indicators + gate booleans + planned geometry; no post-run reconstruction required)

## Presets

- `presets/HYP-MZMS-XAU-M5-007.set` → mode 2
- `presets/HYP-MZMS-XAU-M5-008.set` → mode 3
- `presets/HYP-MZMS-XAU-M5-009.set` → mode 4
- `presets/HYP-MZMS-XAU-M5-010.set` → mode 5

## Status notes

- HYP-006 XAU transfer remains parked invalid engineering (history quality).
- Modes 2..5 implement the frozen 007..010 design candidate; compile/tests do
  **not** authorize Model 0, promotion, paper, or live.
- Default execution remains research-disabled until an AlphaFactory run sets
  `InpResearchAutoMode=true` in the Strategy Tester only.

See `research/LOGIC_TO_CODE_MATRIX.md` and the frozen 007–010 prereg/design
artifacts for the exact boolean surface.
