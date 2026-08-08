# Hot Cache — Current State

Updated: 2026-08-08.

Đây chỉ là handoff cache. Mọi claim phải kiểm tra lại bằng registry, prereg, source, run manifest, report và validator.

## Current state

- Goal: `ACTIVE / UNMET`; xem `01. GOAL/GOAL.md`.
- Workflow canonical: `05. Playbook/WORKFLOW.md`. Tám playbook cũ đã bị thay thế.
- Runtime: MT5-only; trạng thái terminal phải đọc lại bằng `02. AlphaFactory/alpha.ps1 status`.
- Indicator-fusion AIRD/VRC/MBB/QQE/TB: HYP-012..018 chưa cho thấy edge kinh tế. Kết luận chỉ áp dụng đúng logic, dữ liệu, symbol và timeframe đã test; không đóng goal.
- T2 Volman causal grammar là campaign line gần nhất còn cần xác minh từ registry/artifact. Bản full replay gần nhất bị engineering timeout và không tạo result packet; chưa có quyền claim economics, OOS hay promotion.
- Tài liệu vận hành đã được gom về một workflow; mọi thay đổi tiếp theo vẫn phải review/validate/commit trước khi kết thúc task.

## Next action

1. Chạy `git status`, AlphaFactory status, source-of-truth validator và registry validator.
2. Đọc latest registry row cùng artifact của đúng active ID; không suy từ cache này.
3. Lead Quant chọn một thesis causal có phép falsify rõ. Nếu sửa object cũ thì giữ ID đúng contract; nếu đổi mechanism/data/decision surface thì mở ID mới.
4. Đi theo `WORKFLOW.md`: prereg → build → MT5 Model 0/Visual → trade forensics → bounded tuning nếu còn sống → OOS/validation → verdict.
5. Cập nhật failure catalog/strategy log/hot, review diff, quét secret, commit và push khi được phép.
