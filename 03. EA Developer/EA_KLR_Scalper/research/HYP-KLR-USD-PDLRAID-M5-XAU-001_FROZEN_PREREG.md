# Frozen Prereg - HYP-KLR-USD-PDLRAID-M5-XAU-001

Status: **FROZEN BEFORE FIRST COMBINED PROBE** on 2026-07-16.

## Identity and provenance

- Hypothesis ID: `HYP-KLR-USD-PDLRAID-M5-XAU-001`.
- Planned canonical package: `03. EA Developer/EA_KLR_Scalper/`.
- Owner source: `05. Playbook/Strategy/KLR_Scalper_Deep_Research_Report.md`.
- External mechanism source: Federal Reserve H.10 nominal broad U.S. dollar
  index `DTWEXBGS`, obtained through FRED. The report explicitly requires a
  DXY or auditable USD-index proxy for Gold; PO3 HYP-001/002/003 did not use
  an external USD series.
- Feature family: lagged broad-USD-confirmed XAU prior-day liquidity raid,
  M15 structure, M5 displacement/MSS/FVG retest.
- Symbol/timeframes: `XAUUSD`, M15 context, M5 signal/execution.
- Frozen train window: `2022-01-01T00:00:00Z` through
  `2024-12-31T23:59:59Z`. Data from 2025 onward are untouched holdout for this
  hypothesis.
- Future Strategy Tester model: Model `0` only. The offline probe is a kill or
  build screen, never promotion evidence.

## De-dup boundary

The baseline KLR mapping remains closed because its XAU killzone sweep ->
displacement -> MSS -> FVG/retest sequence duplicates killed PO3 and older
Sonic research. This child is allowed one probe only because it adds a
pre-existing report requirement with independent primary-source provenance:
the lagged direction of the broad U.S. dollar index. It also replaces the
Asian-box location with the previous completed New York trading-day high/low.

This is not permission to rescue the family by changing session, threshold,
direction, stop, target, year or subgroup after reading the result.

## Frozen data contract

- XAU bars come only from the portable terminal at
  `02. AlphaFactory/runtime/mt5-portable`; terminal `data_path`, tester root and
  tester-agent files must be physically on `D:`.
- MT5 `commondata_path` is known to remain on `C:` even under `/portable`.
  `FILE_COMMON` is forbidden; the protected C roots are fingerprinted before
  and after any tester run.
- USD data URL:
  `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS`.
- The downloaded CSV and this prereg are SHA-256 bound in the probe receipt.
- To avoid same-day publication lookahead, a trade date may use only the most
  recent USD observation dated at least two U.S. business days earlier. The
  signal is the sign of the one-observation change; zero or missing means
  no-trade.
- The current FRED history is not a vintage/revision archive. Therefore a pass
  can authorize an engineering build, but promotion remains blocked until a
  point-in-time or revision-risk justification is supplied.

## Frozen closed-bar signal contract

- Canonical clock is `America/New_York`, including DST.
- Previous-day liquidity is the high/low of the last completed ET calendar
  trading day with XAU M5 bars. It is frozen before the current day starts.
- Eligible windows are London `02:00 <= ET < 05:00` and New York
  `08:30 <= ET < 11:00`. One challenger trade maximum per ET day.
- M15 bias uses only completed bars and confirmed strength-2 pivots. The last
  two confirmed highs and lows must be HH+HL for long or LH+LL for short; bias
  becomes available only after the M15 close plus two M15 confirmation bars.
- Long setup: M5 low trades below the previous-day low and the same completed
  bar closes back above it, M15 bias is long, and lagged USD change is
  negative. Short is symmetric at the previous-day high with positive USD
  change. No minimum sweep-depth threshold is used.
- Within the next four completed M5 bars, displacement body must be at least
  `1.0 * Wilder ATR(14)` and close beyond the sweep bar's opposite extreme.
  This close is the mechanical MSS.
- The displacement bar must create a strict three-candle FVG. No order-block
  fallback and no minimum gap parameter are allowed.
- Within six completed M5 bars, price must overlap the FVG and close in the
  setup direction inside the same eligible window. Entry is the next M5 open.
- Stop is beyond the sweep extreme by `0.10 * ATR(14)` measured on the sweep
  bar. Target is fixed `2.0R`; maximum hold is 12 M5 bars; hard-flat at the end
  of the active window. Conservative same-bar ordering evaluates stop before
  target.
- Research risk is `0.25%` equity per trade. No compounding is used in the
  offline R-multiple probe.

## Matched controls and cost proxy

- `control_sweep`: same M15 bias, prior-day raid and entry timing, enters next
  M5 open without displacement/FVG or USD gate.
- `control_core`: exact challenger structure/displacement/MSS/FVG rules but
  ignores the USD gate.
- `challenger`: exact `control_core` plus the mandatory lagged USD sign gate.
- Cost proxy is frozen at 35 XAU broker points per round turn. It is an
  explicitly unverified research assumption, not evidence that commission or
  slippage is zero. Metrics are also computed at x1.5 and x2 cost.

## Frozen build surface

`InpRiskPercent=0.25;InpMagic=5600718;InpAtrPeriod=14;InpPivotStrength=2;InpDisplacementAtr=1.00;InpDisplacementBars=4;InpRetestBars=6;InpStopAtrBuffer=0.10;InpTargetRR=2.00;InpMaxHoldBars=12;InpMaxTradesPerDay=1;InpLondonStartMinuteET=120;InpLondonEndMinuteET=300;InpNyStartMinuteET=510;InpNyEndMinuteET=660;InpMaxSpreadPoints=35;InpRequireUsdGate=true;InpUseFileCommon=false`

No parameter optimization is authorized under this ID.

## Pass/kill gates

The challenger may authorize source build only if every condition passes:

- `2.0 <= trades / elapsed calendar week <= 5.0`;
- cost-proxy PF x1 `>= 1.30`, x1.5 `>= 1.25`, x2 `>= 1.00`;
- mean net expectancy at x1 cost `> 0`;
- max drawdown at 0.25% risk/trade `<= 5%`;
- positive net R in at least two of the three train years;
- challenger x1 net R is positive and not below `control_core`;
- challenger x1 PF is at least `control_core PF + 0.15`;
- challenger retains at least 50% of `control_core` trades.

Fail means `KILL_AT_OFFLINE_PROBE`: no `.mq5`, compile or Strategy Tester run
under this ID. Pass authorizes source/audit/compile only. A Model 0 remains
blocked until same-broker spread/commission/slippage provenance and a
hash-bound task packet are available.
