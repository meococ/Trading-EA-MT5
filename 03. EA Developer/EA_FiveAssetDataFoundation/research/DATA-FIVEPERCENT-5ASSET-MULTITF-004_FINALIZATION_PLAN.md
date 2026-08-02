# DATA-FIVEPERCENT-5ASSET-MULTITF-004 Receipt Finalization Plan

Status: FROZEN before finalize-only execution.

Date: 2026-08-02

The dataset-004 production export completed all 20 Parquet files, independently
re-hashed them, and atomically wrote `manifest.json`. Receipt rendering then
failed because a relative authority CLI path was passed directly to
`Path.relative_to(WORKSPACE)` instead of being resolved first.

This plan authorizes no export retry. It authorizes one create-new write only:

`03. EA Developer/EA_FiveAssetDataFoundation/research/evidence/DATA-FIVEPERCENT-5ASSET-MULTITF-004/export_receipt.json`

The finalize-only tool must not import/start MT5, contact a broker, or modify
any Parquet file or `manifest.json`. Before writing the receipt it must:

1. verify hash bindings for this plan, finalizer, tests, original export tool,
   manifest, consumed export authority, finalization blocker and protected-C
   reconciliation;
2. re-hash all 20 exact manifest file paths and verify size/hash;
3. reproduce totals: 48,314,068 rows, 1,206,400,142 bytes, 236 retained rows
   with ambiguous UTC, and 9 exact source duplicates removed;
4. verify zero orders/trades/outcomes and the expected FivePercent D-drive
   terminal metadata already frozen in the manifest;
5. verify the four protected C-drive metadata roots were unchanged;
6. refuse overwrite if an export receipt already exists.

The receipt must disclose that it was recovered from an already-complete
manifest and that the recovery scope was receipt-only. It grants no economic,
T2, promotion, paper, or live authority.
