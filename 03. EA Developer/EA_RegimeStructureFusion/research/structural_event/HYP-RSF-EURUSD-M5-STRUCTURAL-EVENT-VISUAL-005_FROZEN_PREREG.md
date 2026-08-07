# HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-VISUAL-005 — Frozen preregistration

Status: **DIAGNOSTIC DATA ACQUISITION ONLY — NO ECONOMIC AUTHORITY**

Frozen before any STRUCTURAL-EVENT-004 chart was viewed.

## Purpose

Capture one native MT5 Visual Mode loss/win pair for every route that executed
in the terminal development run. The chart must use the real M5 MBB, TB and QQE
indicator EX5 files. AIRD and VRC remain the base EA's hidden calculation
handles so their duplicated panes/dashboard do not obscure price structure.

This campaign cannot rescue, tune or promote
`HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-004`. Its economic verdict is already
terminal because PF and mean achieved R are negative.

## Hash-bound source evidence

- Economic run: `20260807_080936`
- Postmortem:
  `03. EA Developer/EA_RegimeStructureFusion/research/structural_event/HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-004_POSTMORTEM.json`
- Postmortem SHA256:
  `D7D47F40EA4DD2EA5467FF1095DF51CEAE7FFF9E462373745533A23FBC67789C`
- Forensic wrapper SHA256:
  `FCDAB2A46999DF2A884B409C5605B02DA3DEF46C17410AB112140944BE36F590`
- Forensic compile: 0 errors, 165052 bytes.
- Frozen schedule:
  `FROZEN_STRUCTURAL_EVENT_004_OUTCOMES_V1`

## Selection rule

For each of BREAKOUT_LONG, BREAKOUT_SHORT, TREND_LONG and TREND_SHORT:

1. exclude trades whose initial account risk is below 10 USD so the broker
   money-stopout floor cannot choose the chart;
2. select the lowest and highest achieved-R trade;
3. freeze the exact position, entry, exit, SL, TP and visual window before
   viewing;
4. never use a favorable route/year/session slice to alter the terminal
   economic verdict.

## Frozen cases

| Case | Position | Route | Entry server time | Exit server time | Entry | SL | TP | Result | Visual from | Visual to |
|---|---:|---|---|---|---:|---:|---:|---:|---|---|
| SE004-C01-BREAKOUT_LONG-LOSS | 506 | BREAKOUT_LONG | 2019.05.07 13:20:00 | 2019.05.07 14:51:17 | 1.12027 | 1.11923 | 1.12183 | -1.1250R | 2019.04.27 | 2019.05.09 |
| SE004-C02-BREAKOUT_LONG-WIN | 298 | BREAKOUT_LONG | 2018.10.16 09:55:00 | 2018.10.16 10:27:42 | 1.15781 | 1.15674 | 1.15942 | +1.5047R | 2018.10.06 | 2018.10.18 |
| SE004-C03-BREAKOUT_SHORT-LOSS | 4 | BREAKOUT_SHORT | 2018.01.04 10:10:00 | 2018.01.04 11:49:20 | 1.20235 | 1.20380 | 1.20017 | -1.1172R | 2017.12.25 | 2018.01.06 |
| SE004-C04-BREAKOUT_SHORT-WIN | 142 | BREAKOUT_SHORT | 2018.06.05 13:40:00 | 2018.06.05 15:10:43 | 1.16912 | 1.17037 | 1.16724 | +1.5200R | 2018.05.26 | 2018.06.07 |
| SE004-C05-TREND_LONG-LOSS | 202 | TREND_LONG | 2018.07.26 15:45:00 | 2018.07.26 15:55:21 | 1.17192 | 1.16999 | 1.17481 | -1.1036R | 2018.07.16 | 2018.07.28 |
| SE004-C06-TREND_LONG-WIN | 64 | TREND_LONG | 2018.03.06 12:55:00 | 2018.03.06 13:23:43 | 1.23469 | 1.23315 | 1.23700 | +1.5974R | 2018.02.24 | 2018.03.08 |
| SE004-C07-TREND_SHORT-LOSS | 672 | TREND_SHORT | 2019.09.24 09:25:00 | 2019.09.24 09:31:14 | 1.09876 | 1.09911 | 1.09824 | -1.1143R | 2019.09.14 | 2019.09.26 |
| SE004-C08-TREND_SHORT-WIN | 464 | TREND_SHORT | 2019.03.28 12:45:00 | 2019.03.28 13:27:41 | 1.12489 | 1.12589 | 1.12339 | +1.5000R | 2019.03.18 | 2019.03.30 |

## Native acceptance contract

- MT5 Strategy Tester Visual Mode, Model 1 diagnostic replay only.
- No Skip-To.
- Full frozen window must run.
- One 1906x1025 or larger native PNG per case.
- Actual MBB/TB/QQE indicator handles attached to the chart.
- TB focus mode retains only the newest one cell and one void; structural
  labels, cells, void/CE, sweeps and trail remain visible.
- Frozen reference entry, exit, SL and TP must be drawn.
- External capture pause is bounded at 30 seconds.
- AlphaFactory must import the same PNG hash into the matching run directory.
- Missing/blank chart, absent indicator pane, hash mismatch or wrong case is a
  rejected capture.
