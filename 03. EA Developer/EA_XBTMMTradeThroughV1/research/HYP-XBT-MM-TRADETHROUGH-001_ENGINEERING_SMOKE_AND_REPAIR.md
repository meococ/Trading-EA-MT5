# HYP-XBT-MM-TRADETHROUGH-001 — engineering smoke and mandatory repair

## Authority

This checkpoint is engineering-only. The bound task and execution receipt set
`DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE`; no PF, PnL, drawdown, or
candidate-vs-null observation from this run may be used to select or modify the
alpha.

## Reproducible run

- AlphaFactory run: `EA_XBTMMTradeThroughV1/20260812_060159`.
- Source SHA256: `2325EC36FCB94D37C1B68564D6CA888353826DE68D634774C58A044950B44C61`.
- EX5 SHA256: `196C5D46DBCABDC7EB53C38E6EDD2664A07D86EE506161440EF89DAF4F1F9803`.
- Report SHA256: `A6FDC3F38150C03E4FFA0185860C9A7F5742326A024F5D3C304D2F2B8CC12215`.
- Journal SHA256: `1514A9406ED852A55177CD04577C80D8181C56ECE5E189F1C0123A9ECB5A49BF`.
- Fill sidecar SHA256: `B25405C0651BD755103712A33625DB67592A3B61B39B0C2673CDC0494A37C324`.
- Official event stream: 963,512 records; 730,578 quotes; 232,934
  trades; zero timestamp regressions and zero crossed records.
- MT5/AlphaFactory finished in about 16 seconds with 100% native EURUSD
  driver-data quality and `economic_use_forbidden=true`.

The fill sidecar contains 3,644 candidate and 4,088 matched-null maker fills.
Mechanical audit found zero violations of fixed size, 0.5 tick grid, hard
inventory cap, maker fee zero, taker-fee arithmetic, cumulative inverse PnL,
or allowed reason codes. Explicit quote actions respected the 2,000ms interval
and stayed below 3,600 actions/hour. These are engineering facts only.

## Defects found before DESIGN

Adversarial code review after the smoke found five execution/accounting defects
that invalidate this source for economic use:

1. explicit cancel/amend removed the old order immediately instead of after the
   same frozen 400ms outbound latency;
2. funding retirement could leave one side live for two seconds and could match
   a trade at the blackout boundary before risk maintenance;
3. the 45-minute boundary was checked after trade matching;
4. inventory age used one aggregate timestamp instead of FIFO lot provenance;
5. the USD mark-to-market drawdown gate on one XBT collateral measures BTC
   buy-and-hold beta and cannot identify the market-making edge.

The full-size strict trade-through fill remains valid: under BitMEX price-time
priority, a later aggressor print strictly through a live limit necessarily
traversed and consumed that entire better-priced resting order. Touch and exact
price prints remain non-fills.

## Mandatory successor implementation

Before any DESIGN outcome is opened, the source must implement a pending-action
state machine, 400ms cancel/amend latency, deterministic pre-funding retirement,
FIFO lots, pre-match max-age blocking, and XBT-primary strategy NAV/DD. The
one-day engineering smoke must then be repeated under the same no-performance
authority. No threshold, quote size, price formula, fill threshold, direction,
or cost rule may be changed from an outcome.
