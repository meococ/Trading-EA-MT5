# VMOPS-P1b — PHASE 1b: LOOP · VAI TRÒ · WORKFLOW TRÊN CLOUD

Nguồn: spec nguyên văn từ Lead (Linh), gửi qua 2 phần tin nhắn 2026-09-26. File này là nguồn sự thật của task — nếu context bị nén, đọc lại file này, KHÔNG làm theo bản tóm tắt.

## Mở đầu (phần 1)

Nhận MỐC 1+2: kết luận '3 tháng' là ảo giác cache, đúng như Lead nghi; chấp nhận bảng floor (EURUSD M1≥1989, tick (2010-06,2012-06]; XAUUSD M1 2004-06-11, tick (2017-06,2019-06]). Dữ liệu 17 GB đã tải: GIỮ NGUYÊN (dùng lại cho tester, không tải thêm). 8 symbol basket còn lại: KHÔNG đo trong 1b. Vào 1b ngay.

Quy ước mới (ghi vào mục Cloud execution ở B4): mọi task packet của Lead đều lưu thành file `04. Memory/devin_tasks/<TASK-ID>.md`.

## Spec

Nhánh: `devin/vm-ops/phase1b` tách từ `devin/vm-ops/phase1a`. Mở DRAFT PR vào main, ghi rõ "phụ thuộc #2, merge #2 trước". Được commit trên nhánh. Không push main, không merge.

### MỤC TIÊU
Lead giao 1 task packet → Builder chạy đúng `/loop` của repo trên VM, có reviewer context sạch ở các gate, và báo cáo theo template. KPI: task packet → con số/verdict đầu tiên nhanh nhất có thể, không nghi thức thừa.

### NGUYÊN TẮC (giữ như 1a)
- Port và nối cái đã có trong repo; không tạo bản song song.
- Không thêm vai/gate/tài liệu mới nếu nó không chặn được một lỗi đã thực sự lặp lại.
- Một nguồn sự thật: luật nằm trong repo; Devin Knowledge chỉ trỏ vào file.

### VIỆC CẦN LÀM

B1 Port `.devin/` lên cloud (sửa tại chỗ):
   - `.devin/skills/loop/SKILL.md`:
     • Phase 0 thêm bước cloud: `vm_start.ps1`; `vm_doctor.ps1` phải PASS hoặc chỉ WARN trước mọi run; cuối mỗi vòng chạy `vm_cleanup.ps1 -Execute`. Dòng "kill orphan isolate terminals" trỏ sang vm_cleanup khi chạy trên VM.
     • Ghi rõ lệnh cấm `mt5.initialize(path=...)` chỉ áp cho `<OWNER_GUI_TERMINAL>`; attach isolate qua factory_paths là hợp lệ.
   - Advisory board: `run_subagent/subagent_explore` là cơ chế của Devin CLI local. Trên cloud, seat = 1 child Devin session (S0a đã tạo được) với prompt = role card + gate + artifact paths + ban list. Child phải read-only: không commit, không push, không mở process MT5. Output theo contract `VERDICT: PASS|FAIL|WARN` + defect có file:line. Viết cách gọi vào `.devin/agents/README.md`; nếu cần script dựng prompt thì đặt trong `tools/vm/`.
   - `.devin/skills/goal/SKILL.md`: rà path.
   - Nếu S0(b) cho thấy cloud KHÔNG tự nạp `.devin/skills`: thêm đúng 1 Devin Knowledge item trỏ tới `.devin/skills/loop/SKILL.md` + `AGENTS.md`, không chép nội dung (1 card).

B2 Smoke mode trong alpha.ps1:
   - Research trước: `Do-Backtest`, `Assert-ContractReceipt`, manifest, các consumer evidence (`validate_candidate_registry.py`, `validate_ea_delivery_packet.py`, `ea_research_loop.ps1`/`research_loop_engine.ps1`, `build_control_packet.py`, `runs_db.py`).
   - Thêm `backtest -Smoke`: bỏ qua ĐÚNG MỘT điều là ContractReceipt; giữ nguyên pin input, xóa cache .tst, parser, journal, owned-terminal, data-quality. Manifest ghi `tier=smoke` + `plane` (devin-vm-mqdemo trên VM, local-mqdemo trên máy Owner) + terminal build. Output để trong thư mục riêng `runs/smoke/`.
   - Mọi consumer evidence ở trên phải REFUSE run tier=smoke. Test chứng minh cho từng consumer.
   - Đường không-smoke không đổi hành vi: có test "backtest không receipt vẫn bị refuse".
   - STOP: nếu gate receipt dính chặt tới mức thêm -Smoke có nguy cơ làm yếu đường governed → dừng, gửi Lead 2 phương án (flag trong alpha.ps1 vs wrapper riêng gọi lại hàm) kèm rủi ro từng cái.

B3 Vai trò "cloud era": thêm mục vào `.devin/agents/README.md` (không tạo file mới):
   Owner (anh Mèo Cọc): định hướng, GOAL/contract, ký L3+/demo/live, merge PR, tiền/tài khoản · Lead (Linh/Claude): task packet, phản biện, nghiệm thu, giữ luật, báo Owner; không code · Builder (session Devin cloud chính): chạy loop trên VM, sở hữu process mình mở · Reviewer (seat advisory = child session read-only, context sạch): gate A–E · Chart review: Gemini qua Lead · Plane local (máy Owner): MT5 GUI chỉ quan sát qua MCP + dữ liệu venue FivePercent; Devin CLI local chỉ làm việc chỉ-có-trên-máy-Owner (vd git sync).

B4 `05. Playbook/WORKFLOW.md` thêm mục ngắn "Cloud execution":
   - template task packet/báo cáo: TRỎ tới `tools/vm/README.md`, không chép;
   - nhịp: báo ở ranh giới vòng + khi STOP, không chờ "ok" giữa chừng;
   - git: nhánh `devin/<lane>/<task-id>` + draft PR, không merge, commit message có task-id;
   - stop rules: cùng lỗi 2 lần → dừng báo; tối đa 3 vòng build→verify mỗi task nếu chưa có ý Lead; engineering fail ≠ market kill;
   - R1–R7 dẫn chiếu blueprint knowledge;
   - mọi task packet của Lead lưu thành file `04. Memory/devin_tasks/<TASK-ID>.md`.

B5 Chạy thử loop 1 lần, chế độ khô: Phase 0 state load của `/loop` trên VM (đọc GOAL gates, quét registry, tail hot.md, vm_start/doctor) → in status. KHÔNG mint hypothesis mới, KHÔNG chạy governed.

B6 Reviewer thật: mở 1 child session seat **Adversarial Auditor** review PR #2 và PR 1b (diff + test + luật R1–R7). Verdict đăng thành comment trên PR. FAIL thì Builder sửa hoặc giải thích từng defect.

### DoD (kiểm bằng lệnh, dán output then chốt)
1. `vm_start.ps1` PASS trên nhánh 1b.
2. `alpha.ps1 backtest EA_SonicR_PVSRA -Symbol XAUUSD -Period H1 -Smoke`, tháng 01/2024, input contract mặc định → manifest có tier/plane/build; chạy 2 lần → metrics giống hệt; sau đó 0 terminal mồ côi.
3. Test consumer refuse tier=smoke + test không-receipt-vẫn-refuse đều xanh; pytest toàn repo không phát sinh fail mới ngoài 4 fail đã biết.
4. grep `.devin/` không còn path máy; loop có bước cloud; README có Roles cloud era; WORKFLOW có Cloud execution.
5. Output B5 (status loop Phase 0).
6. Verdict reviewer trên PR #2 và PR 1b + cách xử lý từng defect.
7. Link draft PR 1b + báo cáo theo template.

### BACKUP
- Child session không chạy được read-only thật (vẫn commit/push được) → ghi rõ, seat vẫn chạy nhưng prompt cấm cứng + Builder kiểm `git log` nhánh sau review.
- Smoke mode chạm lõi governed → STOP như B2.
- Cùng một lỗi 2 lần → dừng, báo.

Việc `.gitignore` (cache, _scratch, out/, *.parquet, nul…) đang chờ Owner — KHÔNG làm trong 1b.
