# 03. EA Developer

Sự thật package = `& "./02. AlphaFactory/alpha.ps1" list` + contract của EA
đang mở. Graveyard = `00. Old File/EA_Archive/` (gitignore; **không** phải
nguồn compile/evidence).

## Shelf (khớp disk 2026-09-17)

| Path | Vai trò |
|---|---|
| `EA_SonicR_PVSRA/` | Host Sonic R — vẫn compile được, không còn là host bắt buộc (GOAL.md:34-36) |
| `EA_ExecutionKernelHarness/` | Harness compile-check cho `_Shared/`; không phải sleeve giao dịch |
| `EA_LiquiditySweep/` | Sleeve liquidity-sweep (source + artifact thật; HYP-LSWEEP-EUR-M5-001 đã kill trên EURUSD — engineering còn dùng lại được) |
| `_Shared/` | `Execution/AF_ExecutionKernel.mqh`, `MarketData/AF_TickCursor.mqh`, `Telemetry/AF_LifecycleTelemetry.mqh` — shared infra, không phải EA |
| `AI_Regime_Detection/`, `Modern_Bollinger_Bands_GBB/`, `QQE_MOD/`, `SMC_Order_Block_Detector/`, `Volatility_Regime_Classifier_QuantRegime/` | Indicator `iCustom`, không đổi tên thành `EA_*` |

`TB_Smart_Money_Concept_2026` sống ở `TB_Smart_Money_Concept_2026.mq5` (root
repo). Compile: `& "./02. AlphaFactory/alpha.ps1" compile "TB_Smart_Money_Concept_2026"`.

## Fleet mint — đã xóa (Owner 2026-09-17)

~410 dir `EA_*`/`IND_*` probe generated (mint 2026-09-08→11) đã bị xóa hẳn.
Era-2 screen: 26 hypothesis registered → 25 `KILLED_AT_MODEL_0` (PF
0.7–0.9), 1 pending. Verdict kinh tế sống ở
`04. Memory/research/CANDIDATE_REGISTRY.jsonl`, run evidence prune-slim ở
`02. AlphaFactory/runs/`. Đừng đọc tên folder archive như verdict — catalog
failure pattern: `04. Memory/do_not_repeat_failures.md`.

## Đã park (2026-08-31)

94 package `EA_*` nằm ở `00. Old File/EA_Archive/` (gitignore), gồm
`EA_SonicR` classic (GOAL cấm compile cho goal). Park **không** phải kết
luận kinh tế. Khôi phục: `git checkout 61ee7e0 -- "03. EA Developer/<Tên>"`
hoặc copy ngược từ archive.
