# HYP-MULTI-TSMOM-D1-006 DESIGN failure

Verdict: `KILL_BASE_NATIVE_PF_AND_ALL_YEARS_FAIL_NO_COMPARATOR_NO_COST_STRESS`

The final engineering-valid DESIGN baseline used the frozen eight-asset
calendar-365 TSMOM mechanism on `[2018-01-01, 2022-01-01)`. It ran on the
source-prefixed custom-symbol namespace after all eight imports bound correct
origin currencies, calculation mode, contract size and H1/M1/D1 readback.
Every in-tester `OrderCalcProfit` witness passed before the first strategy
decision.

## Accepted run

- Run ID: `20260812_113422`
- Run manifest SHA256:
  `3FFA712EFE8BACE537BFCFEA424BB9A504A0CF85BF1F4389544ED803C8F3DF6C`
- Report SHA256:
  `B14AF2C0AE084323FD547ED97646635E85B82F1388D1319C1497A6C54DCA45A9`
- Enhanced summary SHA256:
  `A04E07E0EFDB47DE0978F1094164ABABCB33EBD47AEF6F599859B6E2A903AAD5`
- Complete journal SHA256:
  `219A2BF60100B15318E769E6DEFA6357498ED3EE545F1C44D0574B12D6EF0C8A`
- Execution receipt SHA256:
  `0BDB6BF589F2A71B16F1A3E05C7B1F5CE54A1440B6FA734766990DF80BFB1947`

## Frozen-gate result

- 208 source-valid Mondays and 208 completed rebalances: cadence gates pass.
- Native PF `0.4853467684` versus required `>=1.25`: terminal fail.
- Native net `-$7,708.23`; expectancy `-$18.01` per reported trade.
- Maximum equity drawdown `7.9451%` versus cap `18%`: pass but cannot rescue
  negative expectancy.
- 2018, 2019, 2020 and 2021 are all negative: `0/4` profitable years versus
  required `>=3/4`.
- Execution telemetry reported one failed transition, which independently
  fails the zero-transition-failure contract.

The native spread baseline already destroys the hypothesis. Per preregistration
the long-only comparator, controlled-cost scenarios, validation, holdout,
optimization and any session/direction/parameter rescue are not opened. The
failure radius is this exact V6 weekly TSMOM identity; it is not a verdict on
independent intraday/scalping mechanisms.
