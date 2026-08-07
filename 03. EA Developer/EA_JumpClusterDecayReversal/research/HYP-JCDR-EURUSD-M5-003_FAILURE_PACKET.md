# HYP-JCDR-EURUSD-M5-003 — terminal failure packet

Status: `KILLED_ROUTER_FEASIBILITY_AND_DATA_PROOF`

This packet closes the exact HYP-003 hard-veto router. It is not a market
no-edge verdict and it does not authorize a same-ID threshold or indicator
rescue.

## Consumed authority

- Authorized attempts: one Model-0, no-trade, outcome-blind router probe.
- Consumed run: `20260807_140336`.
- MT5 test: completed normally in `1:41:45.341`; terminal exit code `0`.
- Report: final balance `10,000.00 USD`, no order rows and no trading deals.
  The sole deal row is the initial `balance` operation, so the EA's raw
  `HistoryDealsTotal()==0` check is a false-negative engineering gate rather
  than evidence of a trade.
- Post-availability price reads, performance metrics and economics: zero.

## Fatal result

The frozen router required all twelve gates simultaneously. It failed:

1. **Data quality:** report History Quality is `49%`, below the strict `>97%`
   requirement. The all-available envelope began in 1971 and cannot establish
   high-fidelity fixed-window evidence for 2016–2020.
2. **Series proof:** AlphaFactory correctly rejected the run because the MT5
   journal contained no structured `DATA_EPOCH_D0_SERIES_PROOF` record.
3. **Coverage:** the EA saw the first requested analysis bar/date and both
   pre/post-window envelopes, but the frozen exact `2020-12-31 23:55` bar did
   not exist in broker history. Exact calendar-end-bar equality is therefore
   not a robust coverage definition for a holiday-shortened session.
4. **Router population:** `934` raw matched events produced only `13` pass
   events (`1.3919%`), `7` long and `6` short, or `0.04992/week` over
   `260.43` elapsed weeks. Frozen gates required at least `150` passes,
   `0.55/week`, and `40` per side.

The gates that did pass were matched arms, no outcome columns, raw count,
year concentration, median stop (`14.20 pips`) and median cost/stop geometry
(`0.10563`). Passing geometry cannot rescue failed cadence or data truth.

## Why the hard-veto design failed

All indicator handles were readable. The problem was semantic overlap, not
missing buffers:

| Hard-veto family | Rejected events |
|---|---:|
| AIRD | 713 |
| VRC | 578 |
| QQE | 413 |
| MBB | 276 |
| TB SMC invalid | 19 |

Largest reasons were `VRC_HIGH_VOL=559`, `AIRD_CONTINUATION=544`,
`QQE_CONTINUATION=413`, `MBB_SQUEEZE=275`, and `AIRD_HIGH_VOL=169`.
Removing any one family in isolation would still leave fewer than 150 passes.
The indicators were measuring overlapping regime/momentum state and were
incorrectly composed as independent fatal AND gates.

Outcome-blind counterfactual counts are diagnostic only. They show that a
materially new role-aware router can be investigated under a fresh ID:

- AIRD and QQE as route/direction evidence rather than hard vetoes;
- VRC and MBB as regime/energy classification;
- TB SMC as causal directional invalidation geometry only;
- JCDR remains the sole event clock.

That is a new decision surface and may not be called HYP-003.

## Bound evidence

- Run manifest: `02. AlphaFactory/runs/EA_JumpClusterDecayReversal/20260807_140336/run_manifest.json`
  — `9D3255E9D7C51D1D49D05AA081390CD8C5CB83232EA2B1410D32B8CB3D9B80E6`
- MT5 report: `02. AlphaFactory/runs/EA_JumpClusterDecayReversal/20260807_140336/report.html`
  — `DDF00D1E9F5F17A50299B5761ACFFFF25CBA04552C3671D2898A542DD3BD7B26`
- Bounded journal delta: `02. AlphaFactory/runs/EA_JumpClusterDecayReversal/20260807_140336/logs/tester_journal_delta.log`
  — `431C494AF5A00C4FCDE8D6B81C88603E60533CF6566F35BB75D4262D36CD107D`
- Router CSV: `02. AlphaFactory/runs/EA_JumpClusterDecayReversal/20260807_140336/logs/EURUSD_JCDR003_StateTelemetry_HYP_JCDR_EURUSD_M5_003.csv`
  — `86C2D5310DF2B6DCC8CF251668BC0B6FEBAA1AECDC1B94CDBE0A7597ED0FE5DB`
- Run summary: `02. AlphaFactory/runs/EA_JumpClusterDecayReversal/20260807_140336/logs/JCDR003_RunMeta_HYP_JCDR_EURUSD_M5_003.json`
  — `4FE95FEDC36C57456D79B53766973E9B475118948B01FD1892DC04DDF0F9F383`
- Streaming analysis: `02. AlphaFactory/runs/EA_JumpClusterDecayReversal/20260807_140336/analysis/jcdr003_router_telemetry_analysis.json`
  — `F50B13C82059D791258E66EDF8CCB820CAD8DCA72A095F41F16A6B5DD6587832`

## Failure radius

Closed permanently: this exact broker-native hard-veto router, its one-shot
Model-0 authority, and any same-ID numeric rescue.

Still reusable: the causal JCDR event clock, matched-arm export contract,
indicator ABI bindings, no-lookahead implementation, streaming log analyzer,
and chart-derived requirement for directional structural invalidation.
