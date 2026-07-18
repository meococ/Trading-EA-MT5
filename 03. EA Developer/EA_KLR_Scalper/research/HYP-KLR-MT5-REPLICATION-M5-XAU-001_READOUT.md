# HYP-KLR-MT5-REPLICATION-M5-XAU-001 - Native MT5 Readout

Date: 2026-07-16  
State: **KILLED_AT_MODEL0_CADENCE**  
Promotion eligible: **No**

## Decision

The Owner was correct that the earlier offline probe was not proof that an MT5
EA had failed. The frozen KLR rules were therefore implemented in the canonical
package, compiled, audited and executed natively in MT5 Model 0. Native tester
evidence now exists, and it confirms that the mechanism is far too sparse for
the frozen strategy objective.

No parameter, session, stop, target, structure rule, USD rule or test window was
changed after reading an outcome. The 2025+ holdout remains unopened.

## Engineering gates

- Canonical source:
  `03. EA Developer/EA_KLR_Scalper/EA_KLR_Scalper.mq5`.
- Source SHA-256:
  `02D6B3B7B99EBD0768FE2EDBC6208A541093D54EF829214538D3FA603852D2F5`.
- Final compile: `0 errors, 0 warnings`; final EX5 size `59,996` bytes.
- Frozen package tests: `7/7 PASS`.
- Snapshot-bound official non-repaint audits: `PASS` for both runs; the only
  bar-zero read is the permitted new-bar gate.
- Embedded USD source SHA-256:
  `15B46514271F0E8D5D721CFEE2FA5A994DB56982E042B55F66F23750B70E8951`.
- Both run manifests bind the same source SHA, include-closure SHA
  `D85AA85C5BC4C13E6230DA8551277B5E913AFD73CDEEED57684B5F686116C40B`,
  broker/server fingerprints, data fingerprint and 2022-2024 Model-0 window.

## Native Model 0 results

Tester identity for both runs: Five Percent Online Ltd,
`FivePercentOnline-Real (Build 6006)`, XAUUSD M5, history quality `99%`,
`212,065` bars and `148,672,555` ticks. Elapsed denominator is `156.5714`
calendar weeks.

| Role | Run ID | Trades | Trades/week | PF | Net USD | Win rate | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Core control (`InpRequireUsdGate=false`) | `20260716_142720` | 4 | 0.02555 | 1.891 | +267.68 | 50.0% | 0.2645% |
| USD-gated diagnostic (`InpRequireUsdGate=true`) | `20260716_142900` | 1 | 0.00639 | 999.99* | +78.74 | 100.0%* | 0.0000%* |

`*` The USD run has one winning trade and no loss, so PF `999.99`, win rate and
drawdown are formatter outputs, not estimable strategy properties.

The frozen cadence target was 2-5 trades per elapsed week. The control reached
only `1.277%` of the minimum cadence and the USD run only `0.319%`. This is a
hard kill independent of cost, PF or the relative comparison.

Lifecycle telemetry reconciles exactly to the reports:

- Control: 4 opens, 4 final closes, 8 deal rows, telemetry net `267.68`; planned
  initial risk ranged from `250.00` to `251.334` USD.
- USD: 1 open, 1 final close, 2 deal rows, telemetry net `78.74`; planned
  initial risk was `250.00` USD.
- No broker-geometry or spread-limit rejection occurred.

## Funnel reconciliation

| Stage | Offline probe | Native MT5 | Native conversion |
|---|---:|---:|---:|
| Prior-day raids | 210 | 346 | - |
| Displacement + MSS | 42 | 61 | 17.63% of raids |
| Strict FVG | 16 | 26 | 42.62% of displacements |
| Retest | 3 | 5 | 19.23% of FVGs |
| USD-aligned retest | 0 admitted entries | 1 | 20.00% of retests |

Absolute counts differ on the FivePercent feed, as preregistered, but the
stage-to-stage conversion is close to the offline funnel. MT5 therefore did
not reveal a hidden high-cadence implementation; it reproduced the same sparse
bottleneck. The native core found four entries rather than two and the USD
branch one rather than zero, but both remain orders of magnitude below the
required cadence.

## Strategy interpretation

- The positive control PF is not actionable with four observations. One London
  winner contributed about `+489` USD while the three New York trades combined
  to about `-222` USD.
- Every native entry was BUY. There is no native short sample and no evidence
  of direction robustness.
- There were no trades in 2022; the control traded twice in 2023 and twice in
  2024. The USD gate retained only the 2024-08-27 trade.
- The USD gate removed 75% of already scarce entries. A one-trade survivor
  cannot show that the external filter improves expectancy.
- Model 0 includes tester spread and reported commission, but independent live
  slippage/fill cost provenance is absent. Cost status is therefore
  `INSUFFICIENT_FOR_PROMOTION`; missing cost is not treated as zero. The cadence
  kill does not depend on resolving that blocker.

## Pair-integrity limitation

AlphaFactory recompiles before every direct backtest. The source and include
closure are identical, but MetaEditor emitted different EX5 hashes for the two
runs (`A1A3...` control versus `183D...` USD). Therefore the preregistered
literal same-EX5 condition is **PARTIAL**, and the relative PF/net delta is not
used as promotion evidence. Each run independently fails the same hard cadence
gate, so this limitation does not rescue the strategy verdict.

## Storage proof

- MT5 install/data/tester roots in both manifests are under
  `D:/Trading EA MT5/02. AlphaFactory/runtime/mt5-portable-fivepercent`.
- `common_files_allowed=false`; the EA does not use the common-file sandbox.
- The protected C common inventory remained exactly `137` files and
  `20,008,308` bytes before and after both tests, with identical metadata hash
  `B4C0D81C79DB307A47B2C94A3CA243E9943B133DB9D97C28A510FC02810E63DC`.
- Reports, manifests, snapshots, logs and analysis artifacts are under
  `02. AlphaFactory/runs/EA_KLR_Scalper/` on D.

## Evidence anchors

- Control report:
  `02. AlphaFactory/runs/EA_KLR_Scalper/20260716_142720/report.html`
  (`41F602DB...BD2E97`).
- Control manifest:
  `02. AlphaFactory/runs/EA_KLR_Scalper/20260716_142720/run_manifest.json`
  (`82E402EC...B43359`).
- USD report:
  `02. AlphaFactory/runs/EA_KLR_Scalper/20260716_142900/report.html`
  (`84AA25A1...AC4C`).
- USD manifest:
  `02. AlphaFactory/runs/EA_KLR_Scalper/20260716_142900/run_manifest.json`
  (`89C5F56C...A9229`).
- Non-repaint audits:
  `20260716_142720/analysis/nonrepaint_audit.json` and
  `20260716_142900/analysis/nonrepaint_audit.json`.
- C-storage snapshots:
  `research/evidence/20260716_KLR_MT5_REPLICATION_C_STORAGE_BEFORE.json` and
  `research/evidence/20260716_KLR_MT5_REPLICATION_C_STORAGE_AFTER.json`.

## Closure

Retain the source and run artifacts for audit/reproduction, but do not rerun or
tune this hypothesis. Reopening KLR requires a materially different causal
mechanism and a fresh preregistration; hour/day/year filtering, weaker
structure/displacement/FVG rules, session changes, RR changes, removing the USD
gate or opening 2025+ are forbidden post-hoc rescues.
