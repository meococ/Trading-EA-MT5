---
name: alpha-ea-runner
description: Run MT5 EA compile+backtest via AlphaFactory with reproducible inputs. Use when you want to run EA backtests (Symbol/Period/From/To/Model/Timeout) and pass overrides in k=v;k=v format, then capture run_id and artifacts.
---

## Quy ước bất biến (bắt buộc)
- Chỉ dùng 1 run/1 thay đổi (ablation).
- Bool overrides dùng `0/1`. Enum dùng int.
- Luôn compile trước khi backtest.

## Lệnh chuẩn (PowerShell, chạy tại `MQL5\\Experts\\Advisors`)
Compile:
- `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" compile "<EA_NAME>"`

Backtest:
- `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\\alpha.ps1" backtest "<EA_NAME>" -Symbol <SYMBOL> -Period <TF> -From "<YYYY.MM.DD>" -To "<YYYY.MM.DD>" -Model <0|1|2> -TimeoutSec <SEC> -Overrides "k=v;k=v;..."`

## Output cần lấy sau mỗi run
- Run folder: `02. AlphaFactory\\runs\\<EA_NAME>\\<RUN_ID>\\`
- Artifacts chuẩn:
  - `analysis\\enhanced_summary.json`
  - `analysis\\datalog\\signals_summary.json`
  - `analysis\\datalog\\trades_summary.json`

## Checklist nhanh
- Xác nhận EA: `<EA_NAME>`
- Xác nhận universe: `<SYMBOL>, <TF>, <FROM>, <TO>, Model`
- Xác nhận overrides: `"k=v;k=v"` (không có khoảng trắng thừa)
- **Cache cleanup:** Xóa file `.set` cũ trong `02. EA\<EA_NAME>\` trước khi chạy version mới (tránh MT5 cache issues)
- Run xong: trích 3 file chuẩn ở trên

## Cache & Set File Management (CRITICAL)
- **Vấn đề:** MT5 có thể cache file `.set` cũ hoặc data cũ, dẫn đến kết quả backtest không đúng với code mới.
- **Giải pháp trước khi backtest:**
  1. Xóa file `.set` version cũ trong `02. EA\<EA_NAME>\` (giữ lại version mới nhất).
  2. Tạo file `.set` mới với tên version rõ ràng (vd `v6.1_XAUUSD.set`).
  3. Luôn dùng `-Overrides` để override parameters thay vì dựa vào `.set` file (tránh cache issues).
- **Nếu kết quả không khớp:** Kiểm tra lại `.set` file và xóa cache trong `02. AlphaFactory\runs\` nếu cần.
