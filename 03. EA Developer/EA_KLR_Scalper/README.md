# EA_KLR_Scalper

Status: `KILLED_AT_MODEL0_CADENCE`; source retained for audit only.

The Owner correctly required native MT5 proof after the original offline kill.
`HYP-KLR-MT5-REPLICATION-M5-XAU-001` therefore built the frozen KLR rules in
`EA_KLR_Scalper.mq5`, passed 7/7 package tests, compiled with zero errors and
warnings, passed both snapshot-bound non-repaint audits, and completed a
FivePercent Model-0 control/USD pair for 2022-2024.

- Core control: run `20260716_142720`, N=4, 0.02555/week, PF 1.891, net
  +267.68 USD.
- USD-gated diagnostic: run `20260716_142900`, N=1, 0.00639/week; PF/WR are
  not estimable from one winner.
- Both fail the frozen 2-5 trades/week cadence gate by orders of magnitude.
- Tester/install/data/artifacts stayed on D; the protected C common inventory
  was byte- and metadata-identical before/after.
- Cost provenance remains insufficient for promotion, but the cadence kill is
  independent of that blocker.

Read `research/HYP-KLR-MT5-REPLICATION-M5-XAU-001_READOUT.md` and the earlier
`research/HYP-KLR-USD-PDLRAID-M5-XAU-001_READOUT.md` before proposing future
KLR work. Do not tune or rerun these IDs. A reopen requires a materially
different causal mechanism and a fresh Owner-scoped preregistration.
