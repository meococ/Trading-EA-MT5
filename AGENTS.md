# AGENTS — Trading-EA-MT5

Authority: Owner request (this message) → `01. GOAL/GOAL.md` → this file →
`05. Playbook/` → verified artifact. `04. Memory/hot.md` is cache, never
authority. MT5 planes / MCP / hooks doctrine: `D:\Meta 5\CLAUDE.md`.

Implement: research first — duplicate / omission / missing-logic /
missing-function checks (`D:\Meta 5\AGENTS.md`). Do not commit or push
unless Owner asked in the current message.

## Indicator / TV→MT5 — làm tới nơi tới chốn (Owner 2026-09-05)

Loop bắt buộc cho mọi việc port/sửa look/gắn chart indicator (Pine/TV →
MQL5). Checklist đầy đủ: `05. Playbook/INDICATOR_WORKFLOW.md`. Không khai
xong khi chưa có snapshot review **PASS**.

```
research TV source+painting → convert plan → implement (reuse, không mint)
→ compile 0 errors/0 warnings + EX5 mới → deploy qua MCP chart_* đúng TF
→ refresh → snapshot đúng cửa sổ MT5 thật → review subagent PASS/FAIL
→ FAIL = quay lại bước 1, ghi lỗi vào Past mistakes
```

Subagent prompts phải nhồi: never `mt5__trade_*`; never `path=` lên Owner
GUI; compile/backtest qua `alpha.ps1`; không worktree trừ
`OWNER_APPROVED_WORKTREE`.

### Past mistakes — không lặp (2026-09-05)

- Nến `default.tpl` (B&W) ≠ overlay SMC; giữ màu Pine TV
  (`#2DD4BF`/`#FB7185`/`#818CF8`).
- HUD `CORNER_RIGHT_UPPER` đè cột giá — HUD LTF = trái-trên; ô HTF không
  chồng HUD.
- Ô H4 spark ≠ chart H4 — muốn SMC trên H4 thì `chart_open` H4 rồi gắn EX5.
- `HtfCountdownText` trả `gap` T7/CN — sai trên crypto và H4 close Saturday.
- `chart_apply_template` song song `chart_add_indicator` → template xóa EX5.
- Đổi corner → xóa prefix object cũ trước khi vẽ lại.
- `OBJ_CHART` không có ANCHOR: inset H4 dùng `LEFT_UPPER` + Y offset; tên
  inset không đặt dưới `HTF_` (RebuildVisuals wipe prefix đó).
- MCP `list_open_charts` không thay snapshot đúng tab đang focus.
