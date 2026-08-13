# Baseline result - HYP-XRV-EURUSD-M15-001

Verdict: `KILL_DATA_COVERAGE_FAIL_SPARSE_NEGATIVE_NO_OOS`.

AlphaFactory run `20260812_020712`, EURUSD M15 Model 0, current broker spread, HQ100, full requested 2018-2021 clock window. Engineering passed: fresh compile `0 errors, 0 warnings`, static synchronization/residual contract `14/14`, runtime_failed=false, no order rejection, and no zero-volume reference bar accepted.

The governing failure is data observability. Of 99,218 potential EURUSD decision bars, only 533 had the required matching current and prior M15 bar timestamps across EURUSD, USDJPY, and GBPUSD. There were 98,717 synchronization/missing-reference skips, for a 99.4951% skip rate versus the frozen 8% maximum. After the 50-observation warm-up, only 32 dislocations, 28 reversion signals, and 23 entries remained.

Observed but non-generalizable performance: 23 trades; net `-$323.47`; PF `0.8011`; WR `47.8%`; expectancy `-$14.06/trade`; max DD `0.6100%`. The chart is a sparse jagged sequence with long gaps and finishes underwater near its worst drawdown. These 23 trades cannot establish economic validity and also fail the minimum 170-trade gate.

Kill the exact synchronized EURUSD/USDJPY/GBPUSD one-bar residual, 2.8 bps dislocation, and 40% five-observation reversion object on this configured tester. Do not relax timestamp synchronization, carry state through missing chronological bars, lower thresholds, tune exits, or use the sparse report for filters. No matched control, OOS, or holdout.

Evidence hashes: source `EF24357569112951955FD034D04F10D5A2D0539F991F2C14FDB7BA404E281054`; EX5 `D2DEB7BCCAF10C3DAB7B7A2FDCE87E2908E78979565A7B1136A08244D09037DF`; report `994B8085F6C8B1656543104BC3EF2813EB352FA1073172B54AF3AFA5EFE58EB9`; journal `7CEACBF6E48C9C9DAEBE56FAF791E77EFECF496F3093509A2413CDA911749D4E`; chart `CC441A659D716075BA8722F65FE546A92DE968C3366BBDDE27A03D396FA14ED5`.
