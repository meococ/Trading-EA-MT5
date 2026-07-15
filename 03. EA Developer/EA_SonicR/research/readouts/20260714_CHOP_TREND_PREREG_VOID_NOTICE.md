# VOID NOTICE — ChopTrend prereg superseded by de-dup fail-closed

Date: 2026-07-14  
Status: `VOID / SUPERSEDED / DO_NOT_MODEL0`

The file `preregs/20260714_H_CHOP_TREND_M15_001_PREREG.md` was drafted under
Owner MT autonomy but is **void** as an authorization instrument.

Authoritative decision:
`readouts/20260714_HYP_CHOP_TREND_M15_001_DEDUP_FAIL_CLOSED.md`
→ `KILL_AT_INTAKE_DUPLICATE / FAIL_CLOSED`.

Reason: CI + EMA cross on USDJPY M15 is the killed `EA_ChopRegime` family
(S629–S631). Removing Mon/Wed/Thu day mining does not create independence.

Do **not** compile `EA_M15ChopTrend`, do not append registry for execution,
do not Model 0 this ID. Sibling `HYP-VOLEXP-M15-001` was Model 0 screened and
**killed** (run `20260714_000432`, PF 1.01) — see
`readouts/20260714_HYP_VOLEXP_M15_001_READOUT.md`. Next price-M15 must be a
**new independent** ID (not Chop/VolCluster/HourOpen/TickVol rescue). USBILL
Model 0 under honest Demo/tester cost is the shortest parallel toward GOAL
gates (still not confirmed without Real/QFSI).
