# ECRS De-dup / Failure-Radius Readout — HYP-ECRS-EURUSD-M5-001

Date: 2026-07-22 (UTC)
Author: parent agent (session: ECRS lane opening)
Scope: pre-registration de-dup for a NEW hypothesis family `ECRS` (Efficiency
Compression Release Scalper) before any probe outcome is computed.
Source thesis: Owner deep-research report
`05. Playbook/Strategy/BaoCao_DeepResearch_ECRS_Efficiency_Compression_Release_Scalper_22Jul2026.docx`
(research input only — grants no backtest/promotion authority).

## 1. Candidate identity (decision-surface decomposition)

| Axis | ECRS object |
|---|---|
| Mechanism | Kaufman Efficiency Ratio ER(10) regime-shift (prior ER < 0.28 AND current ER >= 0.38) as the LEADING gate, conditioned on active ATR(14) compression (ATR <= 0.70 x SMA20(ATR)), confirmed by 12-bar compression-range breakout + tick-volume surge (>= 1.7 x SMA20) + EMA(20) slope bias |
| Information set | Closed-bar M5 OHLC + tick_volume + spread (FivePercent EURUSD shelf); no HTF structure, no VWAP, no news-derived features beyond a blackout filter |
| Decision surface | Entry at next M5 open after all gates true on closed bar; SL 1.6 x ATR; TP 1.6R; 18-bar time stop (probe-simplified exit; full management stack deferred to EA prereg) |
| Symbol/TF/window | EURUSD M5; probe verdict window 2019-2022 (news coverage); sealed holdout 2023->2026-07 reserved for one Model-0 spend |
| Execution/cost | Diagnostic fixed round-turn tiers 1.5/2.25/3.0 pip; static 0.8-pip spread eligibility gate fail-closed |

## 2. Classification: MATERIALLY NEW (open new ID)

Not `same replay`: no prior hypothesis or Sonic strategy ever combined an
ER-regime-shift gate with ATR compression + volume surge + range breakout on
any symbol, and no prior object of any kind was validly tested on EURUSD M5
with this feature family.

Not `post-hoc rescue`: no terminal row's outcome informs any ECRS threshold;
all parameters come from the Owner's pre-outcome deep-research report defaults.

## 3. Adverse priors (declared, not veto) and their exact radius

| Prior | What was tested | Result | Radius vs ECRS |
|---|---|---|---|
| Sonic S191 (EA_VolBreak, USDJPY M15) | compression -> momentum breakout | FAILED PF 0.65; "compression predicts EXPANSION, not DIRECTION" | Closes that object on USDJPY M15. ECRS bets the ER gate supplies the missing direction filter — this is the exact question the probe answers. |
| Sonic S147/S557 (TTM squeeze, USDJPY M15 / XAU) | BB-inside-KC squeeze breakout | FAILED (PF 0.74; WFA 2/5) | Squeeze-lagging finding noted; ECRS uses ATR-ratio compression + ER shift, not BB/KC squeeze. |
| Sonic S534 (EA_VolRegime, XAU M15) | ATR+BBWidth compression -> range breakout, near-identical exit shell | INVALIDATED PF 0.72 | Closes gold M15 vol-expansion breakout. Different symbol/TF/regime gate. |
| Sonic S526/S527 (CompressionORB, GBPUSD M15) | ATR-compression opening-range breakout | FAILED PF 0.96/0.94 | Closes GBPUSD M15 ORB. Reason GBPUSD is NOT the first ECRS symbol. |
| Sonic S597/S598 (XAU M5) | ATR compression breakout / BB squeeze + RSI | DEAD PF 0.78; 3 trades/5yr | Closes gold M5 compression breakout. Not majors. |
| Sonic S664/S665 (KAMATrend, USDJPY M15) | KAMA (ER-embedded) + CI gate | DEAD PF 1.10; "embedded ER regime detection WEAKER than explicit CI" | Strongest ER prior. KAMA smooths ER into an MA; ECRS uses the raw ER level-shift as an explicit gate — different use of the same statistic, never tested. |
| Sonic S677/S679 (TickVolAccel, USDJPY M15) | tick-volume acceleration + body | S679 marginal validation candidate; "retail tick volume = broker-specific noise" | Volume surge in ECRS is confirmation-only; all conclusions conditional on FivePercent feed (declared limitation). |
| HYP-VRAS-EURUSD-M5-003 | tick-volume London-anchor + VWAP/SD + ADX dwell regime scalper | KILLED Model-0 PF 0.5914 N=93 | Radius closes that exact seven-gap object + obvious rescues. ECRS shares only "EURUSD M5 + tick volume as one input"; mechanism, gates, and decision surface are disjoint. |
| HYP-MZMS-XAU-M5-009 | Bollinger/ATR compression envelope breakout, XAU M5 | PARKED INVALID (98% history < 99%) | Never a valid economic kill. ECRS is NOT a revival of this parked-terminal ID: different symbol (EURUSD), different compression definition (ATR ratio vs BB envelope), new leading gate (ER shift). Terminal IDs stay terminal; ECRS opens fresh. |
| do_not_repeat §B "generic compression breakout closed on Sonic fields" | generic squeeze/breakout family | closed frontier | Revival requires a materially different feature set: ECRS supplies ER-regime-shift gating + tick-volume surge, a combination absent from every Sonic field above. Burden of proof accepted: probe must beat matched random + time-shift controls, not just be net-positive. |

## 4. Forbidden-rescue pre-list (binding for this ID)

If the frozen probe KILLs, the following are NOT legal follow-ups under this
ID or a trivially renamed one: threshold retunes (ER pair, ATR ratio, volume
multiple — includes report Variant C 2.2x), session/hour/day/year vetoes,
direction-only splits, swapping the regime-shift definition to the
`ER - ER[2] >= 0.08` delta variant, adding BE/partial/trailing management,
extending into 2023+ data, or re-running on another symbol to shop for a
survivor. A genuinely new mechanism opens a new ID with its own de-dup memo.

## 5. Verdict

`DEDUP_PASS_MATERIALLY_NEW` — open `HYP-ECRS-EURUSD-M5-001`
(ea_name `EA_ECRS_CompressionReleaseScalper`, EURUSD-first; GBPUSD/USDJPY
siblings only after an EURUSD survive, each with fresh data pull + prereg).
