---
name: alpha-nonrepaint-audit
description: Audit EA/indicator MQL5 code for non-repaint / no-lookahead violations (bar 0 leaks, MTF shift mismatch). Use before trusting backtest results or after major logic changes.
---

## Lệnh chạy (PowerShell)
- Quick scan các pattern dễ gây lookahead (cần review thủ công từng match):
  - `powershell -NoProfile -Command "Select-String -Path '.\\02. EA\\EA_SMC_Confluence\\**\\*.mq5','.\\02. EA\\EA_SMC_Confluence\\**\\*.mqh' -Pattern 'CopyBuffer\\(|CopyRates\\(|CopyTime\\(|i(Open|High|Low|Close)\\(|shift\\s*=\\s*0|shift\\s*==\\s*0'"`
- Nếu muốn scan toàn repo EA:
  - thay path `02. EA\\EA_SMC_Confluence` bằng `02. EA`.

## Quy tắc PASS/FAIL (bắt buộc)
- **FAIL** nếu bất kỳ quyết định **signal/entry/exit/filter** dùng dữ liệu **bar 0** (shift=0) của timeframe đang trade hoặc timeframe khác.
- **PASS** nếu bar 0 chỉ dùng cho **visual/debug** (vẽ objects, dashboard) và không ảnh hưởng logic quyết định.

## Checklist review nhanh (bắt buộc)
- Price series: `iOpen/iHigh/iLow/iClose(..., shift>=1)` cho mọi quyết định.
- Indicators/MTF: `CopyBuffer(..., start_pos>=1, ...)` cho mọi quyết định (start_pos=0 chỉ cho hiển thị).
- Volatility/ATR: luôn đọc từ bar đã đóng (shift>=1).
- MTF mapping: không “mượn” bar 0 của H1/H4 để quyết định trên M15.
- Quyết định chỉ chạy tại điểm **nến vừa đóng** (vd `IsNewBar()`), không cập nhật liên tục theo tick rồi vô tình dùng dữ liệu đang hình thành.

## Output mong đợi
- Danh sách các dòng match → review thủ công → ghi note/PR: (1) dòng nào là visual-only, (2) dòng nào cần sửa sang shift>=1.

