# HYP-022 repeated swept-level churn — terminal readout

## Verdict

`KILL_AT_HYP022_COLLECTION_DATA_DENSITY_OR_REDUNDANCY`

HYP-022 is terminal. HYP-023 is not opened. The frozen count cutoff cannot be
changed and the terminal parent family is not reopened. No economic, paper,
live or promotion authority follows from this collection.

## Exact object tested

- Hypothesis: `HYP-ICT-FVG-REPEATED-LEVEL-CHURN-COLLECT-EURUSD-M5-022`.
- Source v1.25 SHA-256:
  `5FF5F8600362C95DAC66C2F1450A2B82D4E1B202F98679B9BE0C52C71039410C`.
- Immutable source snapshot:
  `research/source_snapshots/EA_ICTFVGReportFidelity_HYP-ICT-FVG-REPEATED-LEVEL-CHURN-COLLECT-EURUSD-M5-022.mq5`.
- Frozen plan SHA-256:
  `1A909F222AA22BB39730E2017081524B84EA2B7BEB3D8E1DBD3D0DF9FAED2B67`.
- Frozen preset SHA-256:
  `2C55F4C6EE8E1A150B921A1C5D51F953E8434639EB967B70A70A006305A551EA`.
- Run: `20260720_005836`, EURUSD M5, Model 0,
  `2018.01.01` through `2026.07.19`.
- Run-manifest SHA-256:
  `69AA09F6E73D2EEA79D6208A0097CD01019BDC54B961315D71FB901E72D474C8`.
- Post-run source/binary/run receipt SHA-256:
  `202B0C4100D89469BFB5CCBC3D587E5DF9D3E9BDDBE3176A72FD03B67754B66A`.

## Engineering and provenance

- Package tests: `79 passed`; HYP-022 source contract: `10/10 passed`.
- Compile: `0 errors, 0 warnings`.
- Exact-source non-repaint V21: `PASS`, zero findings.
- History quality: `99%`; tester ticks: `206,517,809`.
- All five required sidecars were hash-sealed. HumanContext and LevelPath each
  contain 6,401 decision rows. LifecycleTrades and TickInitiation contain zero
  data rows. RunMeta records zero attempted/opened entries.
- The generic AlphaFactory economic analyzer returned `No trades found` after
  the report and sidecars were sealed. This is the expected terminal behavior
  for a zero-trade collection and is not treated as an economic result.
- The strict research-loop preflight also requested verified cost provenance.
  No cost compliance was fabricated: the one collection used the existing
  AlphaFactory direct receipt-bound route because trading and performance reads
  were both forbidden.

## Frozen gate result

| Measurement | Result | Frozen gate | Status |
|---|---:|---:|---|
| Confirmations | 6,401 | nonzero, reconciled | PASS |
| Defined paths | 6,399 / 6,401 = 99.9688% | at least 99% | PASS |
| ORDERLY | 5,740 = 89.7015% | at least 20% | PASS |
| REPEATED_CHURN | 659 = 10.2985% | at least 20% | **FAIL** |
| ORDERLY cadence | 12.8700/week | at least 2.0/week | PASS |
| REPEATED_CHURN cadence | 1.4776/week | at least 2.0/week | **FAIL** |
| REPEATED_CHURN 2018–2022 share | 9.9866% | at least 20% | **FAIL** |
| REPEATED_CHURN 2023–YTD share | 10.7385% | at least 20% | **FAIL** |
| Both directions/sessions/years | present for both labels | required | PASS |
| Deterministic external replay | identical SHA-256 | required | PASS |

The canonical result is
`research/evidence/HYP-ICT-FVG-REPEATED-LEVEL-CHURN-COLLECT-EURUSD-M5-022_COLLECTION_RESULT.json`,
SHA-256
`9F0BFD9D1EDCCA31A8816428B3FFEEF52D08FCDE38B5DB5F53F82A18EEF776B0`.

## What the mechanism did and did not learn

Repeated crossing multiplicity is genuinely not recoverable from M5 OHLC.
The closest same-direction comparison found two New-York short decisions only
five minutes apart on 2024-04-16: the first had four favorable-to-adverse
re-entries, the second had zero. Their M5/H1 candle context is almost the same,
which demonstrates that the tick-path bit is real information below candle
resolution.

That fact is insufficient. The repeated-churn state occurs near 10% in both
time splits, so it is too sparse and too imbalanced for the preregistered child
comparison. The full family cannot be rescued by changing `>=2` to `>=1`:
the latter is HYP-020's OHLC-recoverable wick-pierce predicate and was killed
before source work.

The chart package is
`02. AlphaFactory/runtime/ict_fvg_hyp022_collection_receipt/closest_short_pair_charts/cases_manifest.json`,
SHA-256
`0CF4969222B283062DFAEFEC299B611AA7CD3FC9570173F4D414F59FE805B606`.
The blue marker is the measurement decision at the swept level, not an executed
entry; no SL, TP or exit exists. Anatomy bars after the marker are disclosed
only for visual orientation and were not read by the collection parser.

## Legal successor boundary

A successor must change the information object, not the count cutoff. One
legal direction is time-weighted quote-mid resilience: after first favorable
reclaim, compare elapsed time carried on the favorable versus adverse side of
the swept level. A natural 50/50 duration sign is materially different from
cross multiplicity and is not recoverable from OHLC. It must undergo fresh
primary-source review, formal identical-OHLC non-sufficiency, de-dup, frozen
outcome-blind gates and a new hypothesis ID before any source or Model-0 run.
