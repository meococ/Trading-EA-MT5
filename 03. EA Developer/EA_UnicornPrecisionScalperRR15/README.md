# EA_UnicornPrecisionScalperRR15

Owner-directed, post-outcome sensitivity replay for
`HYP-UPS-XAU-M5-008`. The source is derived from the exact frozen HYP-006
Model-0 snapshot and changes only target `2.50R -> 1.50R` plus package,
hypothesis and version identity.

Terminal result: `KILL_DIAGNOSTIC`, Model-0 run `20260716_144508`.
Win rate was 35.606%, Tester PF 0.697 and net -$4,904.75; verified
research-cost PF was 0.475. The 0.991 percentage-point win-rate lift versus
2.50R did not offset worse PF/net/drawdown.

This package is diagnostic-only, `promotion_eligible=false`, and defaults to
alert-only because `InpResearchAutoMode=false`. It does not authorize live
or prop execution, another RR sweep, rerun, or result-derived filters.
