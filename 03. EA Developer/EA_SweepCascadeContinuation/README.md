# EA_SweepCascadeContinuation

Compilable audit package for the terminal EURUSD M5 SCC research family.

Current terminal authority:
`HYP-SCC-MT5-REPLICATION-EURUSD-M5-004` =
`KILL_VALID_MATCHED_PAIR_NO_POSITIVE_EXPECTANCY`.

The frozen 2019-2022 native-MT5 matched pair completed the full 298,483-bar
horizon with exact report/lifecycle reconciliation:

- control `20260725_210715`: N=1,112, PF=0.698096, net=-USD 2,320.05,
  mean realized R=-0.215618;
- HOLD-retest challenger `20260725_210811`: N=261, PF=0.691278,
  net=-USD 587.30, mean realized R=-0.231790, cadence=1.25137/week;
- challenger PF delta=-0.006818 and mean-R delta=-0.016171;
- fixed 1.5-pip / 2.25-pip stress PF=0.354074 / 0.255386.

HYP-004 changed risk from 0.05% to 0.01% only so the unchanged alpha logic
could survive the full tester horizon. It is not an alpha improvement.
Compile is 0 errors/0 warnings, the exact-source
non-repaint audit passes, five GFI chart cases were opened, and the delivery
gate passed with verdict `KILLED`.

A frozen outcome-agnostic random sample (seed `20260725`) then selected
100/261 challenger trades. The first gallery is invalid because broker-server
time was mislabeled UTC. Corrected V2 converted every lifecycle timestamp with
the canonical FivePercent clock, rebuilt 100 decision-as-of plus 100 anatomy
PNGs and matched 200/200 entry/exit markers to UTC M1 with zero missing. Twenty
bounded Grok jobs opened all 200 corrected images and semantic QC reconciled
100/100 identities. Outcome anatomy described 58 tight-stop, 23
immediate-expansion, 15 timeout/no-followthrough and four mixed paths; these
are post-outcome taxonomy, not decision-time predictors or tuning authority.

A separate postmortem source gate now has one executable alternative candidate:
CME Globex 6E continuous MBP-10 pre-entry book state. It is **not** EBS and
cannot rescue HYP004. The offline plan freezes 259 non-empty 120-second windows
from 261 decision clocks, exact `historical-streaming` estimate USD0.254399 /
546,318,080 billable bytes, two source-empty exclusions and a USD1 Owner cap.
The downloader under `research/acquire_cme6e_mbp10_windows.py` is D-only,
SHA/plan-ID/SDK-bound, re-quotes every window before any paid call, journals
each in-flight request, fully decodes DBN, hash-checkpoints outputs and refuses
automatic retry when a charged request cannot be recovered. No paid request,
download, hypothesis or outcome join is authorized yet.

No same-ID rerun, threshold/ATR/R:R/session/direction rescue, optimization,
paper, promotion or live use is authorized. A successor requires a materially
new decision mechanism, fresh de-dup/probe and a new frozen hypothesis.

Primary evidence:

- `research/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_READOUT.md`
- `research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS/pair_analysis.json`
- `research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS/HYP004_GFI_INTEGRATED_READOUT.md`
- `research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_DELIVERY_PACKET.json`
- `research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_CLOSEOUT_RECEIPT.json`
- `research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS/random100_forensics_clock_v2/HYP004_RANDOM100_GFI_CLOCK_V2_READOUT.md`
- `research/20260726_HYP004_POSTMORTEM_EXTERNAL_MECHANISM_SOURCE_GATE.md`
- `research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS/CME6E_MBP10_SOURCE_FEASIBILITY_PLAN.json`
- `02. AlphaFactory/data/databento/cme_6e_mbp10_scc/acquisition_plan.json`

Historical HYP-001 Stage-0 and HYP-002/HYP-003 invalid tester-survival records
remain in `research/` for audit and failure-radius control.
