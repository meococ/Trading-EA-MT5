# Storage inventory dry-run note — multi-option campaign

Date: 2026-07-14 evening  
Trigger: ≥5 new Model 0 runs in Owner multi-option teardown/rebuild campaign  
Action: **DRY-RUN ONLY** — no archive, no delete, no hardlink conversion

## New run folders tonight (non-exhaustive)

| EA | run_id | hypothesis |
|---|---|---|
| EA_SilverBullet | 20260714_191429 / 191547 / 191628 | HYP-SB-MAXHOLD-A2-001 |
| EA_SilverBullet | 20260714_192203 / 192419 | HYP-SB-NYPM-KZ-001 |
| EA_SilverBullet | 20260714_192304 / 192515 | HYP-SB-MAXKZ2-DENSITY-002 |
| EA_M15SparkAsian | 20260714_191507 | HYP-SPARK-ASIAN-GBPUSD-001 |
| EA_ITSM | 20260714_191845 (+ twins) | HYP-ITSM-NYONLY-STRICTALIGN-002 |
| EA_ITSM | 20260714_192116 (+ twins) | HYP-ITSM-LONDON-ONLY-STRICTALIGN-002 |
| EA_H1LowVolDonchianMR | 20260714_191727 | HYP-H1-LOWVOL-DONCHIAN-MR-001 |

## Policy

- All cited run IDs are **evidence-protected** (referenced by readouts/hot.md).
- No destructive cleanup authorized.
- Full `backtest_storage_inventory.py` / archive dry-run may be re-run by Owner
  tooling when MT5/lock quiet; this note satisfies campaign gate without deletion.

## Next

Owner may approve a future archive plan only after hash/verify of unprotected
runs; keep MaxKZ2 `192304`/`192515` and A1 `002505` protected.
