# Readout — HYP-PO3-AMD-SCALP-M5-XAU-002

Verdict: **KILL_AT_OFFLINE_PROBE** on 2026-07-16. No EA source, compile or
Strategy Tester run is authorized under this hypothesis ID.

## Frozen evidence

- Train-only window: XAUUSD M5/H4, `2022-01-01` through `2024-12-31`.
- Bars: 212,339 M5 and 4,644 H4 across 774 ET trading dates.
- Frozen normalized range admitted 729/774 dates, so HYP-001's broker-point
  sample-starvation problem was removed without opening 2025+ holdout data.
- Signal funnel: 121 bias-aligned sweep observations -> 1 displacement+MSS ->
  1 FVG -> 0 valid retests.
- Sweep-only control: N=36, `0.2301` trades/elapsed week, cost-proxy PF
  `0.5107`, net `-10.7072R`, expectancy `-0.2974R`; only 2023 was positive.
- Full PO3 challenger: N=0, 0 trades/week, PF unavailable, net/expectancy 0R.
- Only the cadence-maximum and drawdown gates passed. Cadence-minimum, PF,
  expectancy, positive-years, positive/control net and PF-separation failed.

The normalized range was not the missing edge. The frozen H4 structure plus
displacement/MSS/FVG/retest chain collapsed 121 sweeps to no entries, while the
same sweep family was independently unprofitable. Loosening displacement,
MSS, H4 bias or retest after reading this funnel would be post-hoc rescue and
is forbidden under 002.

## Bound artifacts

- Prereg SHA256:
  `06689A0B76A12E0FE65B41A193DFC4BC7EB1F7E8F650AE7D7AAB702109E62F13`.
- Probe script SHA256:
  `49EF8DEFA2B67F3BB60BE89D81D9635413706380D04380C6E8FB9E362FC927FD`.
- Result:
  `research/preflight/20260716_HYP_PO3_AMD_SCALP_M5_XAU_002_PROBE.json`.
- Result SHA256:
  `1D17A8F7095894E7F330792EBF7B87741161A1FE1BA5E3686F678BCE54896F19`.

This probe used the read-only Python bridge, not MT5 Strategy Tester. Its
workflow-started terminal was stopped after the artifact was written. No
backtest cache/train surface was created or deleted on C; shared history and
configuration remain untouched.

