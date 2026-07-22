# CLAUDE.md

File con trỏ (pointer-only) — không thêm trạng thái dự án hay doctrine vào đây.

Chuỗi đọc-trước, theo thứ tự:

1. `AGENTS.md` — quy tắc vận hành và thứ tự thẩm quyền.
2. `01. GOAL/GOAL.md` — mục tiêu chúng ta đang hướng tới.
3. `INDEX.md` (root) — bản đồ workspace: mọi thứ nằm ở đâu.
4. Registry/prereg/task packet liên quan + AlphaFactory status/lock — contract
   thực thi hiện tại.
5. `04. Memory/hot.md` — cache tham khảo trạng thái gần nhất, không phải authority.
6. `04. Memory/do_not_repeat_failures.md` — prior/failure radius trước
   hypothesis/EA mới, không phải blacklist.

Nguyên tắc nhanh:

- Giao tiếp với Owner và file chỉ dẫn: tiếng Việt. Doc nghiên cứu/evidence
  (hot.md, gates, prereg, readout, registry): tiếng Anh.
- Không trả lời từ trí nhớ khi workspace có artifact kiểm được. Dùng `hot.md` để
  định tuyến rồi xác minh bằng registry/prereg/source/run/receipt hiện tại.
- Failure cũ chỉ đóng đúng ID/candidate identity đã test. Không dùng “no edge”
  của một object cũ để chặn EA mới có mechanism/data contract/decision surface
  mới; mở ID mới, probe rẻ và prereg độc lập, đồng thời cấm post-hoc rescue.
- Không backtest có ý nghĩa nào thiếu `hypothesis_id` + registry row
  (hard rules trong `AGENTS.md`).
- Probe rẻ và offline trước; validation nặng chỉ dành cho survivor.
- Build/fix/complete là outcome-led: tự đi tiếp từ code → verify → chẩn đoán
  trong scope, không chờ Owner nhắc từng bước và không kết thúc ở plan/docs khi
  còn bước triển khai hợp lệ.
- Ceremony phải lean. Compile/test/safety/doc không đồng nghĩa EA đã hoàn thiện;
  chỉ claim theo đúng logic/economic outcome đã được evidence xác nhận.
- Harness EA/backtest: `02. AlphaFactory/alpha.ps1` (+ `alpha.local.ps1` máy
  cục bộ, không commit). Không invent toolchain song song.
- Không commit/push Git trừ khi Owner yêu cầu rõ trong message hiện tại.
- Source shelf/failed (SonicR full ledger + SilverBullet binary + 78 stub
  `.ex5` đã archive THẬT 2026-07-15): `00. Old File/EA_Archive/` — không compile
  làm evidence. Active shelf `03. EA Developer/`: danh sách lane compilable +
  research-only terminal records sống ở `03. EA Developer/README.md`; trạng
  thái kill/park có thẩm quyền nằm ở registry/readout hash-bound, còn `hot.md`
  chỉ tóm tắt. Package có mặt trên shelf không cấp quyền chạy hoặc live.
  File này không liệt kê shelf để tránh drift.
- Đây là dự án cá nhân: mặc định một checkout/một nhánh hiện tại; không tự tạo
  branch, worktree, clone hay nhánh riêng cho sub-agent nếu Owner chưa yêu cầu.
- Doc điều khiển gọn 2 khu: `04. Memory/` (state: hot.md, do_not_repeat,
  registry) + `05. Playbook/` (5 file lõi: gates, runbook, golden_path,
  engineering_standard, research_doctrine). Doctrine cũ (workflow/roster/agents/policies/receipts) →
  archived `00. Old File/project_control_archive_20260716/`.
- Standing: chốt phiên (cập nhật docs + dọn artifact) — parent chủ động sau
  session có ý nghĩa; chi tiết `AGENTS.md` §6.
