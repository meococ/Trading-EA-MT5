# AGENTS — Trading-EA-MT5

Authority: Owner request (this message) → `01. GOAL/GOAL.md` → this file →
`05. Playbook/` → verified artifact. `04. Memory/hot.md` is cache, never
authority. Workspace doctrine for MT5 planes / MCP / attach lives in
`D:\Meta 5\CLAUDE.md`. Do not mint a second copy of those rules here.

Implement: research first (Owner 2026-09-02). Duplicate / omission / missing
logic / missing function — see `D:\Meta 5\AGENTS.md`.

Two-plane MT5 contract: `02. AlphaFactory/session_trader/README.md`; hook
layer: `D:\Meta 5\CLAUDE.md` § Grok hooks + `.grok/hooks/` + `.githooks/`.

Do not commit or push unless Owner asked in the current message.

## Indicator / TV→MT5 — làm tới nơi tới chốn (Owner 2026-09-05)

Mọi việc **port, sửa look, gắn chart** cho indicator (Pine/TradingView → MQL5)
đi vòng này. Không được khai xong khi chưa có snapshot review **PASS**.

Chi tiết checklist: `05. Playbook/INDICATOR_WORKFLOW.md`.

```
1. Research TV     source code + painting (screenshot preview / live chart)
2. Convert plan    TV→MT5 cụ thể (màu, object, HUD, TF, chỗ đặt)
                   nếu chưa có plan → spawn subagent type plan (cố vấn)
                   không implement trước plan
3. Implement       reuse code hiện có; compile 0 errors, 0 warnings + EX5 mới
4. Deploy          gắn lên chart Owner GUI (MCP chart_*), đúng TF
5. Refresh         đợi indicator vẽ xong; không template song song với add
6. Snapshot        chụp đúng chart đang focus (cửa sổ MT5 thật)
7. Review          spawn subagent trung gian (explore hoặc general-purpose)
                   input: ảnh snapshot + đề bài/plan + TV painting
                   output: PASS / FAIL + lỗ cụ thể
8. FAIL            quay lại bước 1. Ghi sai vào mục Past mistakes dưới đây.
                   không vá đè lên lỗi đã biết.
```

Subagent prompts phải nhồi: never `mt5__trade_*`; never `path=` lên Owner GUI;
compile/backtest `alpha.ps1` hoặc MetaEditor `-Wait` vào đúng data folder;
không worktree trừ `OWNER_APPROVED_WORKTREE`.

### Past mistakes (indicator look — 2026-09-05)

Không lặp:

- Đổi indicator sang trắng-đen trong khi Pine TV có màu (`#2DD4BF` / `#FB7185` /
  `#818CF8`). Chart nến B&W (`default.tpl`) ≠ overlay SMC.
- HUD `CORNER_RIGHT_UPPER` đè cột giá. HUD LTF = trái-trên; ô HTF ≠ chồng HUD.
- Ô H4 spark ≠ chart H4. Muốn SMC trên H4 thì `chart_open` H4 rồi gắn EX5.
- `HtfCountdownText` trả `gap` vì T7/CN — sai trên crypto và H4 close Saturday.
- Khai xong mà không snapshot đúng tab; MCP `list_open_charts` không thay ảnh.
- `chart_apply_template` song song `chart_add_indicator` → template xóa EX5.
- Object HUD/HTF sót khi đổi corner — xóa prefix trước khi vẽ lại.
- `OBJ_CHART` không có ANCHOR: `CORNER_LEFT_LOWER` đẩy inset H4 ra khỏi pane —
  `LEFT_UPPER` + Y offset; tên inset dưới `HTF_` bị RebuildVisuals xóa
  (`04. Memory/research/20260905_H4_OBJ_CHART_INSET.md`).
