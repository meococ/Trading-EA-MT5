# 03. EA Developer

Sự thật package = `& "./02. AlphaFactory/alpha.ps1" list` + contract của EA đang mở.
Graveyard = `00. Old File/EA_Archive/` (gitignore; **không** phải nguồn compile/evidence).

## Shelf (khớp disk 2026-09-11)

Package có artifact thật (không phải probe generated):

| Sống | Path | Vai trò |
|---|---|---|
| `EA_SonicR_PVSRA` | `03. EA Developer/EA_SonicR_PVSRA/` | Host Sonic R — vẫn compile được, không còn là host bắt buộc (GOAL.md:34-36) |
| `EA_ExecutionKernelHarness` | `03. EA Developer/EA_ExecutionKernelHarness/` | Harness compile-check cho `_Shared/`; không phải sleeve giao dịch |
| `EA_LiquiditySweep` | `03. EA Developer/EA_LiquiditySweep/` | Sleeve liquidity-sweep, source + artifact thật |

## Generated probes (mint 2026-09-08 → 2026-09-11)

~371 dir `EA_*` + ~39 dir `IND_*` còn lại dưới đây là **probe generated**
(mỗi package một `.mq5` + `.ex5` + `research/CONTRACT.md`), không phải sleeve
đã review. Đừng đọc tên folder như verdict kinh tế; inventory chuẩn qua
`alpha.ps1 list`, hypothesis state qua
`04. Memory/research/CANDIDATE_REGISTRY.jsonl`.

Không phải EA package (Get-EAs bỏ qua, đúng ý đồ):

- `_Shared/Execution/AF_ExecutionKernel.mqh`, `_Shared/MarketData/AF_TickCursor.mqh`
  — consumer duy nhất là `EA_ExecutionKernelHarness`. Chưa có sleeve production nào dùng.
- 6 indicator `iCustom`: `AI_Regime_Detection`, `Modern_Bollinger_Bands_GBB`, `QQE_MOD`,
  `SMC_Order_Block_Detector`, `TB_Smart_Money_Concept_2026`,
  `Volatility_Regime_Classifier_QuantRegime`. Không đổi tên thành `EA_*`.
  `TB_Smart_Money_Concept_2026` sống ở `TB_Smart_Money_Concept_2026.mq5` (root repo).
  Compile: `& "./02. AlphaFactory/alpha.ps1" compile "TB_Smart_Money_Concept_2026"`.

## Đã park (2026-08-31)

94 package `EA_*` nằm ở `00. Old File/EA_Archive/` (gitignore):

- 9 package chỉ có `README.md`, không có canonical `.mq5` → nguồn của 9 warning `Get-EAs`.
- `EA_SonicR` classic — `GOAL.md:36-37` cấm compile cho goal.
- 84 package `EA_*` còn lại — park theo lệnh Owner "chỉ giữ tinh túy".

Park **không** phải kết luận kinh tế. Verdict kinh tế nằm ở
`04. Memory/do_not_repeat_failures.md` và bound theo hypothesis ID, không theo tên folder.

Khôi phục một package:

```bash
git checkout 61ee7e0 -- "03. EA Developer/<Tên>"
```

hoặc copy ngược từ `00. Old File/EA_Archive/<Tên>/`.
