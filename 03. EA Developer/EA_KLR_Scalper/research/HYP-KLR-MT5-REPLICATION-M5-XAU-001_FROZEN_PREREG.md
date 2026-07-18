# Frozen Prereg - HYP-KLR-MT5-REPLICATION-M5-XAU-001

Status: **FROZEN BEFORE SOURCE AND MODEL 0** on 2026-07-16.

## Purpose and authority

- Owner decision: compile and backtest the KLR rules because an offline probe
  is not, by itself, proof that the MT5 EA fails.
- This is an engineering and cross-engine replication hypothesis, not a new
  alpha hypothesis and not a revival of
  `HYP-KLR-USD-PDLRAID-M5-XAU-001`.
- The previous offline kill remains immutable. This lane may determine whether
  native MT5 Model 0 agrees or disagrees with that probe; it cannot promote,
  tune or access the 2025+ holdout.
- Canonical source must be
  `03. EA Developer/EA_KLR_Scalper/EA_KLR_Scalper.mq5`.

## Frozen identity

- Hypothesis ID: `HYP-KLR-MT5-REPLICATION-M5-XAU-001`.
- Parent evidence: `HYP-KLR-USD-PDLRAID-M5-XAU-001`.
- Symbol/timeframes: `XAUUSD`, M15 context and M5 signal/execution.
- Window: `2022.01.01` through `2024.12.31`; 2025 onward remains unopened.
- Tester model: Model `0` only, every tick based on real ticks when available.
- Deposit/leverage: `100000` / `1:100`.
- Storage: MT5 install, data and Tester roots must remain on `D:`. The MT5
  common path on `C:` is not permitted; `FILE_COMMON` must not appear in the
  EA decision or telemetry path.
- Broker identity must be read back and recorded. A different feed from the
  original offline probe is a cross-feed diagnostic, not an exact bar-count
  reproduction.

## Frozen signal contract

- All decisions use completed bars only. Entry occurs on the first tick of the
  next M5 bar after confirmation.
- Canonical clock is ET with U.S. DST. FivePercent server time is converted to
  UTC using GMT+2 winter/GMT+3 European-DST, then UTC to ET.
- Previous-day liquidity is the last completed ET trading-day high/low.
- Eligible windows: London `02:00 <= ET < 05:00`; New York
  `08:30 <= ET < 11:00`.
- M15 bias uses confirmed strength-2 pivots: the last two confirmed highs and
  lows must be HH+HL for long or LH+LL for short.
- Long raid: completed M5 low below prior-day low and close back above it while
  M15 bias is long. Short is symmetric at prior-day high.
- Within the next four completed M5 bars, displacement body must be at least
  `1.0 * Wilder ATR(14)` and close beyond the sweep bar's opposite extreme.
- The displacement bar must create a strict three-candle FVG. No Order Block
  fallback is allowed.
- Within the next six completed M5 bars, price must overlap the FVG and close
  in the setup direction inside the same eligible window.
- Structural stop is the sweep extreme plus/minus `0.10 * ATR(14)` measured on
  the sweep bar. Target is fixed `2.0R`. Maximum hold is 12 M5 bars and every
  position is flattened at session/day end. No BE, partial or trailing logic.
- Maximum one entry per ET day. Spread at entry must be no more than 35 broker
  points.

## Frozen external USD contract

- The exact `DTWEXBGS.csv` snapshot remains hash-bound by SHA-256
  `15B46514271F0E8D5D721CFEE2FA5A994DB56982E042B55F66F23750B70E8951`.
- The source build embeds the dated daily changes needed by 2022-2024; it does
  not read `FILE_COMMON`, use WebRequest or depend on a machine-local path.
- For an ET trade date, only the most recent observation dated no later than
  two U.S. business days earlier may be used. Missing or zero means no-trade.
- Long requires a negative lagged USD change; short requires positive.

## Matched diagnostic pair

Both runs use the same source, EX5, feed, window and all inputs except the one
declared role switch:

- `control_core`: `InpRequireUsdGate=false`.
- `challenger_usd`: `InpRequireUsdGate=true`.

Common frozen overrides:

`InpResearchAutoMode=true;InpEnableTelemetry=true;InpRiskPercent=0.25;InpMagic=5600718;InpAtrPeriod=14;InpPivotStrength=2;InpDisplacementAtr=1.00;InpDisplacementBars=4;InpRetestBars=6;InpStopAtrBuffer=0.10;InpTargetRR=2.00;InpMaxHoldBars=12;InpMaxTradesPerDay=1;InpLondonStartMinuteET=120;InpLondonEndMinuteET=300;InpNyStartMinuteET=510;InpNyEndMinuteET=660;InpMaxSpreadPoints=35;InpServerUtcOffsetWinterHours=2;InpServerUsesEuropeDst=true;InpUseFileCommon=false`

## Decision contract

- Compile must prove a fresh EX5 with zero errors and zero warnings.
- Static non-repaint audit must pass before Model 0.
- Both Model 0 reports and manifests must export successfully and remain on
  `D:`. Tester metrics must include trades, PF, net, drawdown, win rate and
  modeling mode; lifecycle telemetry records actual deals when present.
- Gate counts embedded in RunMeta are compared with the offline funnel. Exact
  equality is not required because the current FivePercent feed is not the
  MetaQuotes feed used by the prior probe.
- If MT5 produces a materially different funnel or economics, classify the
  discrepancy before making a strategy verdict. Do not edit signal parameters.
- If MT5 confirms empty/tiny cadence or poor economics, the KLR strategy has
  native tester evidence for kill/park. If it appears strong, the result is
  diagnostic-only and requires a fresh independent preregistration before any
  further validation.

No optimization, parameter sensitivity, new session, subgroup, year filter or
live/paper attachment is authorized.
