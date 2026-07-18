# HYP-GLDFLOW-XAU-M15-001 — Frozen Preregistration

Frozen: 2026-07-16T07:58:00Z  
State at freeze: official workbook acquired and SHA-bound; no workbook row,
XAU outcome, signal count, or probe result inspected.  
Promotion authority: none. This contract authorizes one closed-bar offline
train probe only.

## Independent causal thesis

SPDR Gold Trust primary-market share creations and redemptions are a direct
daily measure of investor demand/supply for a physically backed gold vehicle,
not another transformation of XAU OHLC. A net creation may represent demand
pressure that persists into the next US cash session; a net redemption may
represent supply pressure. The test deliberately uses the next trading day so
the Trust's prior-day publication is known before entry.

Primary provenance:

- SPDR Gold Shares official product page and Historical Archive:
  `https://www.spdrgoldshares.com/usa/gld/`
- Official archive endpoint:
  `https://api.spdrgoldshares.com/api/v1/historical-archive?exchange=NYSE&lang=en&product=gld`
- The official page states that total shares outstanding is updated during the
  New York day and provides the XLSX Historical Archive. Therefore every row is
  lagged to the next US trading day; same-day use is forbidden.

Frozen workbook:

- Path: `03. EA Developer/EA_GLDFlowPulse/research/data/US_GLD_Archive_EN.xlsx`
- Bytes: `535167`
- SHA256: `8E7F1DA21C7169D1950F865731817E191E897E650454F9FA37AE5AD1CBD08C38`

## De-dup boundary

This is not KLR/PO3/Unicorn/ICT, real-yield, carry, CFTC positioning, OHLC
breakout, or an RR/session rescue. Prior CFTC and GLD-price studies do not test
lagged daily SPDR primary share creation/redemption events. The only price
feature used by the challenger is closed-bar ATR for risk geometry. If archive
inspection shows no daily date plus shares-outstanding field, the hypothesis
is operationally killed without substituting another ETF field.

## Frozen data split and availability

- Symbol/timeframe: `XAUUSD`, M15.
- Train probe: `2022-01-01` through `2024-12-31` inclusive.
- Holdout: every row/bar dated `2025-01-01` or later; must not be loaded,
  counted, summarized, or inspected in this hypothesis.
- Signal source row `t` becomes usable only on the first XAU trading day after
  archive date `t`.
- XAU input must come from the existing MT5 portable data root on `D:`.
- No `FILE_COMMON`; protected MT5 roots on `C:` require before/after inventory
  invariance.

## Frozen signal and execution rules

1. Sort official archive rows by date and use the official total-shares-
   outstanding field only.
2. `delta_shares = shares[t] - shares[t-1]`. Zero/blank delta produces no
   trade. No magnitude threshold, percentile, z-score, smoothing, or subgroup.
3. Direction on the next US trading day: positive delta = long XAUUSD;
   negative delta = short XAUUSD.
4. Entry is the open of the first M15 bar at or after `09:30 America/New_York`.
   DST is resolved with the IANA US/Eastern calendar. Skip if that bar is
   absent; do not substitute another hour.
5. ATR(14) uses completed M15 bars through entry bar minus one. Stop distance
   is `1.50 * ATR`; target is `1.50R`.
6. Maximum hold is 16 M15 bars. The position is closed on the final bar and is
   always flat before the US session ends. No overnight/weekend exposure.
7. If stop and target are both touched within one M15 bar, score stop first.
8. One trade per signal day; fixed research risk is 0.25% only for DD mapping.
9. Research round-trip cost proxy is 82 XAU points at x1, 123 points at x1.5,
   and 164 points at x2. Missing commission/slippage means the result cannot
   promote even if the probe passes.

## Matched control

Use identical signal dates, entry bars, ATR, exits and costs. Control direction
is the sign of XAUUSD change from the last closed M15 bar before entry to the
last available closed bar at least 24 hours earlier (prior-24h momentum). A
zero change produces no control trade. The challenger must beat this control;
the control cannot be changed after results.

## All-or-nothing build-authority gates

Every gate below must pass on the frozen 2022-2024 train:

- challenger cadence `>=2.0` and `<=5.0` trades per elapsed calendar week;
- challenger PF at x1 cost `>=1.35` and net R `>0`;
- PF at x1.5 cost `>=1.25`; PF at x2 cost `>=1.00`;
- expectancy at x1 `>=0.10R`;
- maximum DD at 0.25% risk `<=5.5%`;
- at least 2 of 3 calendar years have positive x1 net R;
- at least 40 long and 40 short challenger trades;
- challenger x1 PF exceeds control x1 PF by at least `0.10` and challenger x1
  net R is not below control x1 net R;
- input hash, availability lag, closed-bar/DST checks, and D-only storage pass.

Failure of any gate is `KILL_AT_OFFLINE_PROBE`: no `.mq5`, compile, Model 0,
threshold edit, direction flip, time change, RR change, or 2025+ access. Passing
all gates permits a separate canonical EA build contract, but does not itself
authorize deployment or promotion.

## Stop conditions

- Workbook hash mismatch, ambiguous/non-daily shares field, same-day leakage,
  unavailable D-portable XAU data, or protected-C mutation: stop fail-closed.
- No live/paper attach and no trading API call.
- One hypothesis, one probe result. Any future economic variant requires a new
  Owner-scoped idea and cannot use this readout to select thresholds.
