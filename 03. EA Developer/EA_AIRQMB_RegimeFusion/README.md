# EA_AIRQMB_RegimeFusion

One-file MQL5 Expert Advisor that consumes the three custom indicators already
maintained in this repository:

- `AI_Regime_Detection` selects BULL, BEAR, RANGE or HIGH-VOL regime.
- `Modern_Bollinger_Bands_GBB` supplies S1 range-fade, S2 trend-continuation
  and S3 squeeze-release events plus stop geometry.
- `QQE_MOD` confirms direction and momentum on completed M5 bars.

## Current verdict

- Engineering: **PASS** — EA and all three indicators compile with 0 errors / 0
  warnings; nine Model-4 real-tick reports completed with reconciled
  `lifecycle-v3` entry/final-close telemetry.
- Economic: **KILL** — all nine frozen baselines have PF below 1.0 and negative
  expectancy.
- Promotion: **FAIL** — no optimization, validation, paper or live authority.

The EA source is `EA_AIRQMB_RegimeFusion.mq5`. It is intentionally a single
`.mq5` file, but it requires the three compiled custom-indicator EX5 files in
`MQL5/Indicators/AlphaFactory/` at runtime.

## Frozen baseline setup

| Parameter | Value |
|---|---:|
| Timeframe | M5 |
| Risk per trade | 0.25% |
| AI minimum confidence | 0.45 |
| Stop | 1.00 x MBB half-width, with broker/spread floor |
| Target | 1.50R |
| Maximum spread/stop | 0.15 |
| Maximum trades/day | 3 |
| Entry cooldown | 5 bars |
| Maximum hold | 48 bars |
| Trading window | 07:00–20:00 UTC |
| Account drawdown lock | 8% |

These values are reproducible engineering defaults, **not recommended trading
settings**. The preregistered per-symbol confidence/RR grid stayed locked
because no baseline survived the PF, expectancy and drawdown screen.

## Signal routing

| AI regime | MBB event | QQE confirmation | EA lane |
|---|---|---|---|
| RANGE | S1 re-entry | primary/secondary RSI extreme and recovery | range fade |
| BULL / BEAR | S2 basis pullback | same-side zero-line momentum | trend continuation |
| BULL / BEAR | S3 squeeze release | same-side zero-line momentum | breakout |
| HIGH VOL | any | any | no new entry |

All signal buffers are read at shifts 1 or 2. Current-bar time is used only to
detect a newly opened M5 bar, after which the EA evaluates the completed bar.

## Evidence

- `research/HYP-AIRQMB-MULTI9-M5-SCREEN-006_RESULTS.md` — nine-symbol results
  and semantic-lane failure radius.
- `research/screen006_results.json` — machine-readable result summary.
- `research/HYP-AIRQMB-MULTI9-M5-SCREEN-006_FROZEN_PREREG.md` — frozen
  baseline and conditional optimization contract.
- `research/HYP-AIRQMB-MULTI9-M5-SCREEN-006_NONREPAINT_AUDIT.json` — manual
  source-bound audit.
- `research/HYP-AIRQMB-EURUSD-M5-SCREEN-006_NONREPAINT_TOOL_TRIAGE.md` —
  conservative scanner findings and call-site triage.

Build with:

```powershell
.\02. AlphaFactory\alpha.ps1 compile "EA_AIRQMB_RegimeFusion"
```
