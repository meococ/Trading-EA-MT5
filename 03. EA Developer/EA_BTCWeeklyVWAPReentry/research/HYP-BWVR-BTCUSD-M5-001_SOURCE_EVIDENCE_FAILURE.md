# HYP-BWVR-BTCUSD-M5-001 — source evidence failure

Verdict: `KILL_SOURCE_ATTEMPT_ENGINEERING_EVIDENCE_LOSS_NO_SOURCE_OR_ECONOMIC_VERDICT`

## What happened

The sole durable attempt `BWVR-SOURCE-001` was claimed and then stopped with
the combined exception `row/order gate failed`. The analyzer raised that one
message for either of two different conditions: DESIGN rows below 400,000 or
non-increasing `source_epoch` order.

The failure terminal does not preserve the observed DESIGN row count, the
chronology result, per-gate results, a report, a ledger or a receipt. Therefore
the attempt cannot prove which source gate failed. The full-file manifest makes
an under-row-count result plausible after filtering 2018–2022, but that is an
inference and is not authoritative source evidence.

## Evidence boundary

- Prereg SHA256:
  `678AAEDCE480F8853CBE4A3D3AFC1D7C5968F28E62276A571E34FD2E9D76C213`.
- Analyzer SHA256:
  `39B2AF7B9EFE21964DD65646FFB7678A17DA6310C61B6434E9379B3F43D81A0E`.
- Test SHA256:
  `EF405A412234301C74B5E3C08C0EE234755AD713D893097A9CBBDC8385670824`.
- Attempt-start SHA256:
  `CF272590A3DFB1AE3734ECA9277FD67A151A199349860A796CD3CCF62BA0C9F6`.
- FAILED terminal SHA256:
  `2925945DA5CC4B7EA14A74D1D1A14955B85F5146C4D9D2F7892026733D2D762B`.
- Source file was opened only inside this consumed source attempt. No outcome,
  next-bar price, MQL5, MT5, order, trade, PF, cost, validation or holdout was
  opened.

## Consequence

`BWVR-SOURCE-001` is consumed and same-ID retry is forbidden. Do not lower the
row floor, merge the two validation conditions, retry the scan or label the
weekly-AVWAP mapping source-infeasible. A future unrelated source attempt must
first prove capability from manifest metadata and must write a structured
failure receipt containing input hashes, observed row counts and every gate
result even when the attempt fails.
