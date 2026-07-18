# Frozen Prereg — HYP-PO3-AMD-SCALP-M5-XAU-003

Status: **FROZEN BEFORE FIRST PROBE** on 2026-07-16. This is the report's
independently pre-declared New York branch. It does not change the terminal
London-session HYP-001 or HYP-002 decision surfaces.

## Identity and bounded rationale

- Hypothesis ID: `HYP-PO3-AMD-SCALP-M5-XAU-003`.
- EA package: `EA_PO3_AMD_Scalper`; parent: terminal HYP-002.
- Source: Owner-authorized
  `05. Playbook/Strategy/PO3_AMD_Scalper_Deep_Research_Report.html`.
- Feature family: XAU PO3/AMD New York kill-zone continuation using completed
  Asian liquidity, H4 structure, displacement, MSS and FVG retest.
- XAUUSD M5/H4 train window: `2022.01.01` through `2024.12.31`; 2025+ remains
  untouched holdout data.
- HYP-001 prereg explicitly deferred the report's NY continuation to a
  separate hypothesis before any PO3 result was read. This ID spends that one
  remaining branch; a failure ends this report build lane rather than opening
  more sessions or weakening signal gates.

## Frozen closed-bar contract

- Canonical timezone: `America/New_York`, including US DST.
- Completed Asian box: `20:00 <= ET < 03:00`, assigned to the following ET
  trading date; use its high, low and median closed-bar M5 Wilder `ATR(14)`.
- Range normalization remains exactly HYP-002:
  `1.3333333333 <= range / median Asia ATR(14) <= 15.0`.
- NY manipulation and confirmation window: `07:00 <= ET < 10:00`.
- H4 bias remains strength-2 HH+HL plus discount for long or LH+LL plus
  premium for short, available only after the H4 close.
- Sweep the completed Asian boundary by at least one point and close back
  inside in the bias direction; M5 `ATR(14) >= 15` points.
- Within three completed M5 bars: body `>= 1.5 * ATR(14)` and close beyond the
  last confirmed strength-2 pre-sweep M5 pivot (MSS).
- A standard three-candle FVG must form on the displacement bar. Within six
  completed bars and before 10:00 ET, a bar must overlap the FVG and close in
  the intended direction. Enter at the next M5 open.
- One sweep-only control and one full-composite challenger maximum per ET day.

## Frozen management, cost and EA surface

- Risk 0.25% equity; one owned symbol+magic exposure; one trade/day.
- SL sweep extreme plus 40 points; BE at 1R; 50% partial at 2R; final 3R.
- Time stop after 30 minutes without reaching 1R; max hold 90 minutes; hard
  flat by 16:00 ET. Stop wins intrabar ambiguity.
- Cheap-probe cost proxy remains 35 points/trade and remains unverified.
- Historical news filter remains disabled because no hash-bound calendar
  exists; no promotion without verified cost and news provenance.

`InpResearchAutoMode=true;InpEnableTelemetry=true;InpRiskPercent=0.25;InpMagic=5600718;InpAtrPeriod=14;InpAsiaMinRangeAtr=1.333333;InpAsiaMaxRangeAtr=15.0;InpSweepMinPoints=1;InpDisplacementAtr=1.50;InpDisplacementBars=3;InpSwingStrength=2;InpRetestBars=6;InpSlBufferPoints=40;InpTargetRR=3.00;InpBreakEvenR=1.00;InpPartialCloseR=2.00;InpPartialClosePct=50.00;InpTimeStopMinutes=30;InpMaxHoldMinutes=90;InpMaxSpreadPoints=20;InpMaxTradesPerDay=1;InpDailyLossPct=1.50;InpMaxAccountDrawdownPct=5.00;InpServerUtcOffsetHours=2;InpSessionManipStartHourET=7;InpSessionManipEndHourET=10;InpSessionEntryEndMinuteET=600;InpRequireNewsGuard=false`

## Frozen pass/kill gates

All must pass: 2.0–5.0 trades/elapsed week; cost-proxy PF >=1.50;
expectancy >=0.40R; drawdown at 0.25% risk <=5%; at least two positive train
years; challenger net R positive and no worse than control; challenger PF at
least 0.20 above control.

A pass authorizes canonical source build and code gates, not promotion. A fail
terminally kills 003. No session, direction, threshold, year, SL/TP, H4, MSS,
displacement, FVG or retest edit is allowed after reading the result.

