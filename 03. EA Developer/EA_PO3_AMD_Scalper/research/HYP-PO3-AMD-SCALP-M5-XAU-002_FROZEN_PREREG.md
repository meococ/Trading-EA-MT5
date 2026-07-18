# Frozen Prereg — HYP-PO3-AMD-SCALP-M5-XAU-002

Status: **FROZEN BEFORE FIRST PROBE** on 2026-07-16. This is a fresh,
dimensionally normalized mechanism hypothesis. It does not modify or rescue
the terminal `HYP-PO3-AMD-SCALP-M5-XAU-001` result.

## Identity and provenance

- Hypothesis ID: `HYP-PO3-AMD-SCALP-M5-XAU-002`.
- EA package: `EA_PO3_AMD_Scalper`.
- Parent: `HYP-PO3-AMD-SCALP-M5-XAU-001` (`KILLED_AT_OFFLINE_PROBE`).
- Source: Owner-authorized
  `05. Playbook/Strategy/PO3_AMD_Scalper_Deep_Research_Report.html`.
- Feature family: XAU PO3/AMD with an ATR-normalized completed Asian range,
  H4 structure, sweep, displacement, MSS and FVG retest.
- Symbol / timeframe: `XAUUSD` / `M5`, with H4 bias.
- Frozen train window: `2022.01.01` through `2024.12.31`. Calendar year 2025
  and later remain untouched holdout data.
- Future Strategy Tester model: Model `0` only. The cheap probe is not an MT5
  backtest and cannot itself promote the EA.

## Why this is a new mechanism

Hypothesis 001 interpreted the report's `80..300` XAU range as raw broker
points. On this broker that admitted only 6 of 774 ET dates, so the probe did
not test the full PO3 sequence. The report also supplies an M5 ATR context of
roughly `20..60` points. Before reading any normalized result, 002 replaces
only the dimensionful range gate with the report-derived envelope:

`80 / 60 <= completed Asian range / median completed-Asia ATR(14) <= 300 / 20`

or `1.3333333333..15.0 ATR`. This removes broker-digit dependence while
preserving the report's own range/volatility scale. No observed percentile,
winning subgroup or result-derived threshold is used.

## Frozen closed-bar signal contract

- Canonical session timezone: `America/New_York`, including US DST.
- Completed Asian box: `20:00 <= ET < 03:00`, assigned to the following ET
  trading date. Its high, low and median Wilder M5 `ATR(14)` are frozen only
  after 03:00 ET.
- Manipulation: `03:00 <= ET < 05:00`; entry confirmation must close before
  04:30 ET. This avoids the report's overlapping 02:00/03:00 lookahead.
- H4 bias: last two confirmed strength-2 pivot highs and lows form HH+HL for
  long or LH+LL for short. Long price must be at/below the confirmed range
  midpoint; short is symmetric. H4 information becomes available only after
  the H4 bar closes.
- Sweep: at least one broker point beyond the completed Asian boundary and a
  close back inside in the H4-bias direction.
- M5 ATR floor: Wilder `ATR(14) >= 15` broker points.
- Within the next three completed M5 bars, candle body must be at least
  `1.5 * ATR(14)` and close beyond the last confirmed pre-sweep strength-2 M5
  pivot (MSS).
- A standard three-candle FVG must form on that displacement bar. No order
  block fallback is allowed.
- Within six completed M5 bars, price must overlap the FVG and the bar must
  close in the intended direction before 04:30 ET. Entry is the next M5 open.
- At most one control and one challenger observation per ET trading date.
  The control enters the next M5 open after the same-direction sweep close and
  is used only to test whether the full composite adds value.

## Frozen management and research limitation

- Risk `0.25%` of equity; one owned symbol+magic exposure; one trade/day.
- SL beyond the sweep extreme plus 40 points; BE at `1R`; close 50% at `2R`;
  final target `3R`.
- If `1R` is not reached within 30 minutes, close at that bar's close. Maximum
  hold 90 minutes; hard flat by 16:00 ET.
- Intrabar ambiguity is conservative: stop is evaluated before favorable
  milestones on the same bar.
- Cheap-probe cost proxy: 20 spread + 8 round-turn slippage + 7
  commission-equivalent points = 35 points/trade. This is an unverified report
  assumption, not same-broker cost provenance.
- Historical news blocking is disabled because no hash-bound calendar input
  exists. Any promotion remains blocked until a fail-closed calendar and
  verified same-broker spread/commission/slippage contract are present.

## Frozen EA decision surface

`InpResearchAutoMode=true;InpEnableTelemetry=true;InpRiskPercent=0.25;InpMagic=5600717;InpAtrPeriod=14;InpAsiaMinRangeAtr=1.333333;InpAsiaMaxRangeAtr=15.0;InpSweepMinPoints=1;InpDisplacementAtr=1.50;InpDisplacementBars=3;InpSwingStrength=2;InpRetestBars=6;InpSlBufferPoints=40;InpTargetRR=3.00;InpBreakEvenR=1.00;InpPartialCloseR=2.00;InpPartialClosePct=50.00;InpTimeStopMinutes=30;InpMaxHoldMinutes=90;InpMaxSpreadPoints=20;InpMaxTradesPerDay=1;InpDailyLossPct=1.50;InpMaxAccountDrawdownPct=5.00;InpServerUtcOffsetHours=2;InpRequireNewsGuard=false`

## Pass/kill gates

The frozen probe passes only if every condition is true:

- `2.0 <= trades / elapsed calendar week <= 5.0`;
- cost-proxy PF `>= 1.50`;
- mean net expectancy `>= 0.40R`;
- max drawdown at 0.25% risk/trade `<= 5%`;
- positive net R in at least two of the three train years;
- challenger net R is positive and not below the sweep-only control;
- challenger PF exceeds control PF by at least `0.20`.

If the probe passes, source may be built and screened. A legal Model 0 still
requires the exact decision surface above, lifecycle-v3 telemetry, non-repaint
audit, matched control, and verified cost provenance. No threshold, session,
direction, year, SL/TP or subgroup may be changed after reading the result.

