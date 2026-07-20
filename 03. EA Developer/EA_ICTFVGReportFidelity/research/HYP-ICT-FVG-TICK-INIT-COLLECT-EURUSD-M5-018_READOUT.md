# HYP-018 collection readout — terminal kill

## Verdict

`KILL_AT_HYP018_COLLECTION_DATA_DENSITY_OR_REDUNDANCY`

HYP-018 completed its one authorized outcome-blind Model-0 collection in run
`20260719_235851`. The run is valid as a collection: source and receipt identity
match, history quality is 99%, 206,517,809 tester ticks were replayed, all four
required sidecars were sealed, 6,401 unique profiles reconciled, and no order was
attempted or opened. Economics are undefined because the run intentionally
contains zero trades.

## Frozen-gate result

| Gate | Result | Evidence |
|---|---:|---|
| Engineering | PASS | 65 current package tests; run compile 0 errors / 0 warnings; non-repaint V20 PASS |
| Model-0 identity and tick coverage | PASS | Exact source SHA `41536FFC...CDA40`; 103 contiguous monthly TKC files; 99% history quality |
| Zero-trade boundary | PASS | Entries attempted/opened = 0; LifecycleTrades data rows = 0 |
| Profile identity/reconciliation | PASS | 6,401 unique confirmations; confirmation bar equals profile bar; sidecars and RunMeta agree |
| Defined fraction | PASS | 6,401 / 6,401 = 100% |
| Agree density and coverage | PASS | 5,435 rows; 12.1861 per elapsed week; both directions, both sessions, every year 2018–2026 |
| Materiality | **FAIL** | Sign-nonagree share is 15.0914% pooled and 10.1202% in 2018–2022, below the frozen 20% floor |
| Deterministic replay | PASS | Same canonical result SHA on two parser runs |

Materiality shares:

- 2018–2022: agree 89.8798%, nonagree 10.1202%.
- 2023–YTD: agree 77.8991%, nonagree 22.1009%.
- Pooled: agree 84.9086%, nonagree 15.0914%.

## Mechanism diagnosis

The sign-only quote-mid tick-rule statistic is mostly a redundant encoding of
the already required directional confirmation candle. HYP-012 accepts only a
large directional body that closes through the opposite sweep-bar extreme and
in the outer 25% of its range. A majority sign of within-bar mid changes usually
agrees with that terminal displacement by construction. The 2018–2022 block
makes this redundancy especially clear.

This does not show that real-tick path information is useless. It shows that
**net sign count over the entire confirmation bar** is not sufficiently distinct
from the OHLC confirmation already in the scaffold. Mining imbalance magnitude,
tick count, spread, year, session, or direction thresholds would be a prohibited
post-hoc rescue and is not authorized.

## Research boundary and legal next direction

- HYP-019 is not opened; no economic test of the sign-agreement gate is legal.
- HYP-012, HYP-014, HYP-017, and HYP-018 remain terminal.
- A future idea must measure a different mechanism before outcome access. A
  defensible candidate is **within-bar event ordering** around the swept level
  (breach → reclaim latency → hold/revisit behavior), because path order is not
  recoverable from the final OHLC bar and is distinct from full-bar net sign.
- Historical cost provenance remains failed independently; any later economic
  survivor remains diagnostic until that blocker is solved.

## Bound artifacts

- Result: `research/evidence/HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018_COLLECTION_RESULT.json`, SHA-256 `947F1B81...7932E`.
- Run manifest: `02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_235851/run_manifest.json`, SHA-256 `A39295E8...0D702`.
- Post-run source/binary receipt: `research/evidence/20260719_SOURCE_BINARY_RECEIPT_V25.json`, SHA-256 `325DCC28...2C20`.
- Immutable source snapshot: `research/source_snapshots/EA_ICTFVGReportFidelity_HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018.mq5`, SHA-256 `41536FFC...CDA40`.

No paper, live, promotion, threshold tuning, or repeat HYP-018 run is authorized.
