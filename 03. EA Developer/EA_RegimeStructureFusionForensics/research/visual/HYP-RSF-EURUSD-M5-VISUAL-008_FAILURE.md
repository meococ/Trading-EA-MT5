# HYP-RSF-EURUSD-M5-VISUAL-008 — Failure Packet

Status: `KILLED_ENGINEERING_DIAGNOSTIC`

## What passed

- EA compile: zero errors; AlphaFactory run completed at `20260807_025341`.
- RunMeta now reports `EA_RegimeStructureFusionForensics`, matching the run
  manifest.
- Native MT5 Visual Mode image imported as
  `NATIVE_MT5_VISUAL008_EURUSD_M5.png`, `511050` bytes, SHA-256
  `F8FEE53A0E4BF7288E1BCFEEDCABAE2EBAA7C593BA257899D6468C2AF27E006D`.
- Direct QQE display-handle probe succeeded for all eight requested buffers:
  `qqe_probe_mask=255`.

## Root cause and kill reason

At the smoke bar the probe returned:

- histogram `0.00000000`
- trend line `38.92190514`
- primary RSI `23.82971866`
- secondary RSI `44.46095257`
- state `0`
- all three histogram mirrors `0.00000000`

The live RSI values rule out a dead handle and the all-valid mask rules out a
CopyBuffer or warm-up failure.  The native pane showed the same result: a white
trend line with no columns.

The displayed indicator short name and exact value shift reveal the underlying
ABI defect: MQL5 includes `input group` declarations in positional `iCustom`
arguments.  The former QQE call omitted group placeholders.  Consequently the
first group consumed Primary length, values shifted left, and Secondary
threshold received Bollinger length (`50`).  That suppresses the histogram and
means the parent EA's QQE decision handle was also not using its intended
parameters.

This is a fidelity failure, not evidence for parameter rescue.  VISUAL-008 is
killed and authorizes no economic conclusion.  A fresh ID must bind the QQE
Primary, Secondary and Bollinger group placeholders; grouped display calls for
MBB/TB must be aligned at the same time.  Historical Cell-16 QQE conclusions
remain terminal for their tested implementation and cannot be relabeled as a
correct-parity result.
