# Frozen Prereg — HYP-GMP-XAU-M15-REALYIELD-001

Status: **FROZEN BEFORE FIRST PROBE** on 2026-07-16.

## Research provenance and independence

- Package: `EA_GoldMacroPulse`; symbol/timeframe: `XAUUSD` / M15.
- Train: `2022.01.01` through `2024.12.31`; 2025+ is untouched holdout.
- External source: Federal Reserve Board H.15 10-year inflation-indexed
  Treasury constant-maturity yield, FRED series `DFII10`.
- Train snapshot:
  `research/data/DFII10_2019_2024.csv`, 1,566 rows, SHA256
  `C22544C463731D9EE153B5C87D53FCE2B45DF606841263E9F40E833071A0ADED`.
- Official H.15 is posted at 16:15 U.S. Eastern. An observation dated `t` can
  affect a trade only on the first later XAU trading date with a 14:30 UTC M15
  bar. No same-day H.15 value is used.
- Primary rationale: Federal Reserve Bank of Chicago research identifies an
  inverse relationship between expected long-term real rates and gold after
  2001. This is an external opportunity-cost mechanism, not another OHLC
  sweep, FVG, range, session, volatility or momentum filter.
- Browser ChatGPT Deep Research was attempted first but no browser backend was
  available. This packet is explicitly a primary-source web fallback and may
  not be represented as GPT-5.6 Sol Deep Research output.

## Frozen signal and matched control

- Compute `delta_yield = DFII10[t] - DFII10[t-1]` from consecutive published
  observations.
- Eligible shock: `abs(delta_yield) >= 0.05` percentage points (5 basis
  points). No percentile or observed-outcome threshold is used.
- Challenger direction is inverse to the real-yield shock: falling real yield
  -> long XAU; rising real yield -> short XAU.
- Entry: first XAUUSD M15 open at exactly 14:30 UTC on the first trading date
  after observation date `t`.
- Matched control uses the same eligible dates, entry, stop, target, hold and
  cost, but direction is the sign of the last completed 24-hour XAU return.
- All market predicates use completed bars. No bar-zero signal, future H.15
  value, current-bar close or outcome field is available at entry.

## Frozen management and cost screen

- Wilder M15 ATR(14) from the bar completed before entry.
- Initial SL distance `1.5 * ATR`; TP `1.5R`; stop wins same-bar ambiguity.
- Maximum hold 26 M15 bars; otherwise exit at the final completed-bar close.
- One challenger and one matched-control observation per eligible shock date.
- Research cost proxy: 82 XAU broker points per completed trade, equal to the
  current D-side same-broker M1 spread P99 clue. Commission and slippage remain
  missing, so even a pass is not promotion-eligible.
- Research risk mapping: 0.25% per R, no compounding in the cheap probe.

## Frozen pass/kill gates

The challenger passes only if every condition is true:

- `2.0 <= trades / elapsed calendar week <= 5.0`;
- cost-proxy PF `>= 1.35`;
- mean net expectancy `>= 0.10R`;
- max drawdown at 0.25% risk/trade `<= 8%`;
- positive net R in at least two of three train years;
- challenger net R is positive and no worse than the matched momentum control;
- challenger PF exceeds control PF by at least `0.10`.

Pass authorizes source design only. It does not authorize Model 0 until a
same-broker commission/slippage manifest and an immutable runtime external-data
contract exist. Fail terminally kills this ID; no yield threshold, entry hour,
direction, stop, target, hold, year or subgroup rescue is allowed.

## Frozen future EA surface

`InpResearchAutoMode=true;InpEnableTelemetry=true;InpRequireExternalData=true;InpExternalSignalFile=DFII10_2019_2024.csv;InpRiskPercent=0.25;InpMagic=5600719;InpYieldShockBp=5;InpEntryHourUTC=14;InpEntryMinuteUTC=30;InpAtrPeriod=14;InpStopAtrMult=1.50;InpTargetRR=1.50;InpMaxHoldBars=26;InpMaxSpreadPoints=82;InpMaxTradesPerDay=1;InpDailyLossPct=1.00;InpMaxAccountDrawdownPct=8.00`

