# HYP-ICT-FVG-FULLCHART-NODD-EURUSD-M5-009 - diagnostic readout

Verdict: **INVALID_DIAGNOSTIC_EARLY_BROKER_STOP_OUT_AND_RUNMETA_IDENTITY_MISMATCH**

## What was changed

The canonical HYP-008 source was reused. The control preset changed only
`InpMaxAccountDrawdownPct=8.00` to `100.00`, which functionally removed the
persistent account-DD gate while leaving the signal, entry, stop, target,
0.25% risk, daily loss, trade-count and cooldown rules unchanged.

## What happened

AlphaFactory run `20260719_131410` opened 162 control trades from 2 January to
25 April 2019. It lost USD 10,202.30, PF was 0.5813, win rate 42.59%, expectancy
was -USD 62.98/trade and reported max DD was 9.96%.

This was not a full-chart run. The tester stopped on 25 April after a broker
position stop-out at only 23,349 bars / 4,972,379 ticks, about 7% of the
configured 2019-2022 interval. The final position therefore has no normal
lifecycle final-close row. The no-DD preset exposed that the 8% EA gate had
previously prevented the losing control from reaching the broker/tester
stop-out boundary.

The run also reused the source-embedded HYP-008 identity, so RunMeta and sidecar
names identify HYP-008 while the AlphaFactory manifest correctly identifies
HYP-009. That identity mismatch independently makes the observation unsuitable
as a hash-bound full-chart result.

## Decision

The planned challenger arm was not run because the matched control failed the
full-window and identity gates. The full-fidelity challenger remains a distinct
pre-execution zero-trade object; removing account DD cannot create trades when
the signal never calls execution.

The only legal continuation is a fresh diagnostic child that binds its own
source identity and uses micro-risk solely to keep the tester alive through the
whole chart. Dollar P&L from that continuation is scale-diagnostic only. It
cannot rescue HYP-008, demonstrate prop compliance, authorize promotion or
access the sealed 2023+ holdout.
