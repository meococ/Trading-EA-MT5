# Hot Cache — Current State

Updated: 2026-08-10.

Đây chỉ là handoff cache. Mọi claim phải kiểm tra lại bằng registry, prereg, source, run manifest, report và validator.

## Current state

- Goal: `ACTIVE / UNMET`; xem `01. GOAL/GOAL.md`.
- Workflow canonical: `05. Playbook/WORKFLOW.md`. Tám playbook cũ đã bị thay thế.
- Runtime: MT5-only; trạng thái terminal phải đọc lại bằng `02. AlphaFactory/alpha.ps1 status`.
- Campaign retrospective hiện hành: `04. Memory/research/EA_CAMPAIGN_RETROSPECTIVE_2026-08-10.md`. KPI là time-to-first-admissible-untuned-baseline; governance-only không tính là market progress.
- `HYP-JCDR-EURUSD-M5-006` đã có baseline hợp lệ và bị KILL: 562 trades, cadence 2.1568/week, PF 0.763972 sau report costs, price-only PF 0.851207, expectancy âm và equity DD 8.02%. Không được cứu bằng filter/session/R:R/hold-time.
- Supertrend/STBS không còn là lane ưu tiên. Giữ artifact như evidence nhưng không mở thêm comparator/parser/governance child để tiếp tục cùng thesis.
- Chỉ một market mechanism được active. Tối đa hai engineering revisions trước baseline; revision thứ ba cần opportunity-cost PASS độc lập.
- Worktree đang có hàng trăm artifact chưa checkpoint; không seal whole-worktree path-set. Chỉ bind scoped source/config/prereg và attempt-local outputs.

## Next action

1. Chọn đúng một indicator mechanism materially fresh và de-dup bằng registry/failure catalog.
2. Viết prereg ngắn + source-to-spec matrix + boundary/index fixtures trước khi freeze identity.
3. Dùng AlphaFactory chuẩn: focused tests → compile → non-repaint → một untuned Model-0 baseline trong cùng ngày; không tạo custom governance chain nếu CLI hiện hữu chạy được.
4. Triage ngay: PF xa 1.30 và raw/pre-cost edge âm, không có implementation defect thì KILL mechanism; chỉ baseline sống mới được mở cost stress/validation/OOS.
5. Cập nhật failure catalog/strategy log/hot, review diff, quét secret và tạo scoped checkpoint; không đụng phần dirty không thuộc task.
