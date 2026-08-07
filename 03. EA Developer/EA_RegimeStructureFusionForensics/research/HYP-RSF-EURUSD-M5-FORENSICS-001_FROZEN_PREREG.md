# HYP-RSF-EURUSD-M5-FORENSICS-001 â€” Frozen forensic replay

Frozen after the terminal Block-1 verdict and after selecting the cases, but
before viewing any price/indicator chart for those cases. This is a diagnostic
replay of the already-consumed Cell 16 outcome, not a new economic trial and
not a parameter-rescue attempt.

## Bound source and population

- Parent run: `EA_RegimeStructureFusion/20260806_210021`, variant
  `B1C16_UNION_FULL`, EURUSD M5, 2018-01-01 through 2022-12-31, Model 0.
- Parent EA SHA-256:
  `E40F29431E8ADA440302F7DEDB7ACD8EBCB48C1308EB6B43936849C128E959D0`.
- Parent lifecycle SHA-256:
  `E3008DFC3DE3EF5C149E052100374B14679D7F9E7F499C95BF1B943B8C0A957B`.
- Parent Cell-16 contract receipt SHA-256:
  `3A0927F43C89FF60C22DBD7065E8E89486E10ABCB56B8D29BA6388721C79D7E5`.
- Forensic wrapper SHA-256:
  `F08F6FB01456738536EB72E68D9CAB184ABC92D37345168DB2F5A8E403CF5839`.
- Wrapper includes the parent source; it does not edit its decision, sizing,
  order, stop, target, cooldown, or session logic.
- Frozen selection manifest SHA-256:
  `EF01DE5A9424B972F2C6115273843C7C30F5D6D6507D8F48932F3E236A89803C`.
- Frozen cases CSV SHA-256:
  `1012C7F46F92E91800B461DA8C3749238E74088D0B64E85385F19353290CFD23`.

The 14 cases were selected without chart or indicator inspection: one loser
nearest the negative median R for each of the six engine/direction strata, one
matched winner per stratum, plus the global minimum- and maximum-R trades.
This prevents attractive-chart cherry-picking.

## Replay contract

- Replay the full 2018-2022 window so AIRD online state and every recursive
  indicator receive the identical history sequence.
- Use the exact Cell-16 inputs: session mask 6, mode mask 7, context/TB/QQE
  enabled, manual profile, current tester spread, 100,000 USD, 1:100.
- Export closed-bar snapshots only inside the 13 frozen capture windows. The
  short input token `FROZEN_13_V1` selects dates hard-bound in source so the
  MT5 input serializer cannot truncate the window definition.
- Required snapshot fields: all AIRD posterior probabilities/regime/confidence,
  VRC regime/direction/volatility percentile, MBB basis/bands/squeeze/signals,
  TB bias/swings/cell/void/structure/sweeps/displacement, QQE states, and the
  source bar OHLC.
- Fidelity gate: exactly 670 final trades and the same parent net/PF within
  report precision; every selected position must map to a decision snapshot.
- If fidelity fails, no chart interpretation is allowed until the export path
  is repaired and rerun without changing the parent trading logic.

## Chart and analysis contract

For each case create two distinct artifacts:

1. `as-of`: only information available at entry, with the entry bar at the
   right edge; it must not reveal exit, P/L, or subsequent bars.
2. `anatomy`: entry through exit plus a bounded post-exit context window,
   showing SL/TP and realized outcome.

The analysis must first describe the full 670-trade population, then compare
the frozen matched pairs. Images are explanatory evidence, never the sampling
mechanism. Findings must cite the exact EA decision logic and distinguish
measured evidence from chart interpretation. At most three new mechanisms may
be proposed; each requires a fresh hypothesis ID and a separate preregistered
test. No threshold, timezone, direction, or exit parameter is authorized for
tuning under this forensic ID.

## Authority

This replay can explain why the tested Cell-16 stack failed. It cannot revive
`HYP-RSF-EURUSD-M5-BLOCK1-001`, authorize validation/holdout access, claim an
edge, or promote the EA.
