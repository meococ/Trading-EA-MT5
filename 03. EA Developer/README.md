# 03. EA Developer — Active Shelf

Updated: 2026-07-15 (docs↔disk reconcile)

Active shelf = 2 lane. Mọi package khác đã archive THẬT sang
`00. Old File/EA_Archive/` (2026-07-15) — **không** compile từ đó làm evidence.

| Active package | Path | Notes |
|---|---|---|
| `EA_FVGConfluence` | `03. EA Developer/EA_FVGConfluence/` | Owner Path-C override BUILD — FVG M5 + confluence; **not** promotion-ready |
| `EA_HybridICT_Sonic` | `03. EA Developer/EA_HybridICT_Sonic/` | Path-C stub (KILL@Model0, 0 trades); lane riêng |

| Archived (2026-07-15) | Archive path | Ghi chú |
|---|---|---|
| `EA_SonicR` | `00. Old File/EA_Archive/EA_SonicR/` | full research ledger; bản duy nhất (vẫn còn trong `origin/main` history) |
| `EA_SilverBullet` | `00. Old File/EA_Archive/EA_SilverBullet/` | **binary-only** (`.ex5`); không còn source `.mq5` |
| 78 stub `.ex5` | `00. Old File/EA_Archive/` | binary compile không-nguồn (không tracked); manifest trong cleanup_receipts |

Manifest: `00. Old File/project_control_archive_20260716/cleanup_receipts/20260715_docs_disk_sync_archive.json`.
Live scope / blockers / next moves: `04. Memory/hot.md`.
Workspace map: `INDEX.md`. Do not compile from `00. Old File/` as valid evidence (`AGENTS.md`).
