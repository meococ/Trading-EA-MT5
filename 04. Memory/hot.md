# Hot Cache — Current State

Updated: 2026-08-31.

Cache. Không phải authority. Sự thật live: `01. GOAL/GOAL.md`.

## Next action

GOAL UNMET.

**CACHE ONLY — ba dòng dưới không có row trong `CANDIDATE_REGISTRY.jsonl`
và không có artifact trong `02. AlphaFactory/runs/` (thư mục không tồn tại).
Đọc như routing hint, không phải số liệu ledger.**

- IBRK Fast-Kill `20260827_085615` PF 0.88 N=533 @ 1.46/wk.
- I1PB Fast-Kill `20260827_141109` PF 0.95 N=134 WR 20% @ 0.37/wk
  (WHQ không bù London hour-10 PF 0.00). Không IBRK-002 / I1PB-002 /
  đảo fade / salvage NY. Holdout kín.
- Host **H4AT-001** magic 16082776 v4.86 1R flatten 21. H4AT best PF
  living 1.76 nhưng ~0.26/wk — **trượt cadence DONE 2–5/tuần** của GOAL.
  IBRK_* / I1PB_* là reject-reason token bên trong host
  (`EA_SonicR_PVSRA/Include/SNR_Signal.mqh`), không phải package rời.

Next: family mới. Không H4AT-002 / 1R session-clone / session-box.

## Repo state (2026-08-31)

Shelf còn 2 package: `EA_SonicR_PVSRA` (host) + `EA_ExecutionKernelHarness`.
94 package đã park ở `00. Old File/EA_Archive/` — park là dọn dẹp, không phải
verdict kinh tế. Baseline git `61ee7e0` + zip
`D:\Meta 5\backups\Trading-EA-MT5-20260831-pre-cleanup.zip` giữ nguyên bytes.

**Python trên máy này là Microsoft Store stub — không chạy.** Mọi action
`alpha.ps1` gọi `python` (`validate`, `monte`, `wfa`, `cpcv`, `robust`,
`param`, `analyze`) đang chết cho tới khi cài Python 3.12 thật.
