# Quy Trình Phát Triển Chiến Lược Kinh Tế (Economic Strategy Pipeline)

Doc này quy định đường dẫn phát triển duy nhất cho các chiến lược trading tìm kiếm edge kinh tế.

## Các Bước Thực Thi Chuẩn

1. **Intake Brief & Logic-to-Code Matrix**:
   - Chuyển thesis của trader thành rule định lượng: Entry, Invalidation, SL/TP, Trailing/Management, Risk, Cost.
   - Gán đúng vai trò `context | qualification | trigger | invalidation | risk` cho từng quan sát.
   - Tín hiệu entry CHỈ dùng bar đã đóng (`shift >= 1`).

2. **Probe Rẻ (Offline Scanner / Label Proof)**:
   - Tái sử dụng probe SDK trong `02. AlphaFactory/tools/research/`.
   - Kiểm tra failure radius trong `04. Memory/do_not_repeat_failures.md` trước khi thử.
   - Probe fail -> `parked/killed`, dừng lại không code EA.

3. **Freeze Hypothesis & PREREG**:
   - Khóa `hypothesis_id`, symbol, timeframe, exact overrides, matched control, budget thử nghiệm.
   - Đăng ký row trong `CANDIDATE_REGISTRY.jsonl`.

4. **Build EA Package Canonical**:
   - Source canonical: `03. EA Developer/<EA>/<EA>.mq5`.
   - Audit non-repaint qua `02. AlphaFactory/tools/audit_mql5_nonrepaint.py`.
   - Biến đổi `input string` trong preset/tester inputs ghi plain `key=value` (không tuple format).

5. **Model 0 Backtest qua Guarded Research Loop**:
   - Chạy `ea_research_loop.ps1` với `-Model 0`.
   - Reconcile `report.html` ↔ `LifecycleTrades` ↔ `RunMeta`.

6. **Post-Run Routing (Heavy-Delivery / Fast-Kill)**:
   - Nếu vi phạm fatal gate đã prereg -> Chuyển sang `pipeline_fast_kill.md`.
   - Nếu vượt gate necessary -> Chạy Heavy-Delivery Forensics: Multi-TF Anatomy Casebook, Sub-agent / Grok Visual Review (nếu cần), và build EA Delivery Packet (`alpha.ps1 delivery`).
