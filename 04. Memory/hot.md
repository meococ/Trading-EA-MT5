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

## Toolchain (2026-08-31 — đã chạy thật, không phải suy đoán)

- **Python 3.12.10** cài user-scope. Trước đó là Microsoft Store stub 0 byte,
  nên mọi action `alpha.ps1` gọi `python` và toàn bộ 251 file `.py` đều chết.
- `alpha.ps1 validate` → exit 0. `alpha.ps1 status` → 0 warning.
- `alpha.ps1 compile EA_SonicR_PVSRA` → **0 errors, 0 warnings**, EX5 67348 B.
  Compile chạy được mà **không** phải tắt terminal Owner (PID 7712).
- pytest: **357 pass / 29 fail / 1 skip**. 29 fail đều là thiếu hụt có sẵn
  (research contract JSON chưa từng có trong checkout, `external/` gitignore,
  `tool_runbook.md` / `ea_golden_path.md` mất, registry hỏng ở dòng 286).
- `session_trader`: 12/12 module pass. OBSERVE đã chạy thật trên terminal
  Owner — `read_only=true`, `orders_sent=0`, `time_mapping_verified=true`.
  `DEMO_EXECUTE` vẫn khoá chờ EA executor MQL5 canonical.

## Hai mặt phẳng MT5

- **Research** — `alpha.ps1` + portable isolate dưới `02. AlphaFactory/runtime/`.
  Nơi duy nhất có thẩm quyền kinh tế. Pin ngoài runtime bị throw.
- **Observation** — MCP `127.0.0.1:22346` + `session_trader probe`, trỏ vào
  terminal GUI Owner. Chỉ đọc, không sinh evidence.
- Chi tiết trong `AGENTS.md` § Quy trình thực thi.

## Repo state (2026-08-31)

Shelf còn 2 package: `EA_SonicR_PVSRA` (host) + `EA_ExecutionKernelHarness`.
94 package đã park ở `00. Old File/EA_Archive/` — park là dọn dẹp, không phải
verdict kinh tế. Baseline git `ac02500` + zip
`D:\Meta 5\backups\Trading-EA-MT5-20260831-pre-cleanup.zip` giữ nguyên bytes.
