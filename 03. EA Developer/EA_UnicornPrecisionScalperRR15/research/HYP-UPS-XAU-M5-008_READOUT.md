# HYP-UPS-XAU-M5-008 — RR 1.50 sensitivity readout

## Terminal verdict

`KILL_DIAGNOSTIC`. The Owner-directed post-outcome replay is complete and
`promotion_eligible=false`. Lowering the target from 2.50R to 1.50R did not
repair expectancy, cadence, drawdown or robustness. No live/prop execution,
rerun, alternate RR, subgroup veto or threshold rescue is authorized.

## Identity and validity

- Run: `20260716_144508`, FivePercent `XAUUSD M5`, Model 0,
  `2024.01.01–2025.12.25`.
- Diagnostic package: `EA_UnicornPrecisionScalperRR15`.
- Source SHA256:
  `EB262B51BB19F66A4AD6F771D0275756EA5C3D58B6E717558326B66FCF52FC4D`.
- The 4/4 replay contract proves the source differs from frozen HYP-006 only
  by target `2.50R -> 1.50R` and operational package/hypothesis/version
  identity. Compile was 0 errors / 0 warnings.
- Snapshot-bound audit passed all eight source/include files with no
  repaint/lookahead finding.
- Lifecycle reconciliation: 132 OPEN, 132 final CLOSE, 132 unique positions,
  no partial closes and zero non-positive initial-risk rows.

## Direct RR comparison

| Metric | HYP-006 2.50R | HYP-008 1.50R | Change |
|---|---:|---:|---:|
| Trades | 130 | 132 | +2 |
| Wins / losses | 45 / 85 | 47 / 85 | +2 wins, same losses |
| Win rate | 34.615% | 35.606% | +0.991 pp |
| Tester PF | 0.7242 | 0.6971 | -0.0270 |
| Tester net | -$4,396.90 | -$4,904.75 | -$507.85 |
| Average win | $256.54 | $240.22 | -$16.32 |
| Average loss | -$187.54 | -$190.53 | -$2.99 worse |
| Max DD | 5.461% | 5.512% | +0.051 pp |
| Trades / elapsed week | 1.2569 | 1.2762 | +0.0193 |
| Full-cost PF x1 | 0.4982 | 0.4753 | -0.0229 |
| Full-cost PF x1.5 | 0.4129 | 0.3908 | -0.0221 |
| Full-cost PF x2 | 0.3433 | 0.3216 | -0.0217 |

At 1.50R the realized average payoff ratio was only about 1.261
(`240.22 / 190.53`), so the break-even win rate was about 44.23%. Actual
win rate was 35.61%, an 8.62 percentage-point deficit. The earlier target
added only two winners while reducing average winner size and slightly
increasing average loss. This is a negative-expectancy entry/management
distribution, not a target-distance problem.

## Cost, path and stability

- Verified research-cost proxy x1: PF `0.4753`, net `-35.8234R`.
- Cost x1.5: PF `0.3908`, net `-45.9176R`.
- Cost x2: PF `0.3216`, net `-56.0118R`.
- Robustness: `0/7`; bootstrap PF 95% CI `0.445–1.042`.
- Monte Carlo P95 drawdown: `7.315%` versus frozen limit `5.50%`;
  probability of finishing below start was 100% under trade-order
  resampling.
- Fixed-parameter temporal diagnostic: only `1/5` OOS windows profitable,
  average OOS PF `0.80`.
- Equity audit: `REJECT`; 370 days without a new high, 60% losing months,
  R² `0.7099`, median trade `-$60.50`, and 109-trade recovery.

Unified validation produced 3 PASS, 8 FAIL and 3 BLOCKED gates. The BLOCKED
items are missing observed request/fill slippage reconciliation and an
identical enhanced-summary rewrite; they prevent promotion but do not weaken
the kill because Tester PF, full-cost PF, cadence, DD, Monte Carlo,
robustness and equity all independently failed.

## Storage closeout

All retained run/tester/report evidence is on `D:`. Protected
`C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\Common\Files`
was identical before and after: 137 files, 20,008,308 bytes, metadata SHA256
`B4C0D81C79DB307A47B2C94A3CA243E9943B133DB9D97C28A510FC02810E63DC`.
The run created no disposable C payload, so zero C files were deleted.

## Evidence

- Report:
  `02. AlphaFactory/runs/EA_UnicornPrecisionScalperRR15/20260716_144508/report.html`
  (SHA256 `1C9E03A1F77A5520BD1C0A7D9DDB4DC45CE6BCDB175AE8D217DA5860047C1D66`).
- Run manifest:
  `02. AlphaFactory/runs/EA_UnicornPrecisionScalperRR15/20260716_144508/run_manifest.json`
  (SHA256 `204AE22A34B65228BF39FEA759D6A38B57CD6E538150731F6D9EB268F803A372`).
- Validation summary SHA256:
  `06B3D0EC9204F5B34952DFD6167DBFACF446F1961C7BE33587DC804ECC157E16`.
- Verified cost artifact SHA256:
  `F8BC6AAF0FE19859F79AC56AB34AD91C7822C6BEE6A1E53A0936BD0AE08F3321`.
- Run non-repaint audit SHA256:
  `E5D3B02243D1FACA06474C3D81AF8687A952926924EE551BF86F829908A57EEB`.
