# CLAUDE.md

Pointer-only. Không ghi trạng thái dự án, metric run hay doctrine chi tiết vào
file này.

## Chuỗi đọc-trước bắt buộc

1. `AGENTS.md` - authority, vai trò Lead Quant và hard rules.
2. `01. GOAL/GOAL.md` - outcome kinh tế; lane lịch sử không phải live status.
3. `INDEX.md` - bản đồ nguồn canonical.
4. Registry/prereg/task packet liên quan + AlphaFactory status/lock - quyền chạy.
5. `04. Memory/hot.md` - cache handoff ngắn; xác minh lại bằng artifact.
6. Trước candidate mới, tìm mechanism/ID liên quan trong
   `04. Memory/do_not_repeat_failures.md` và registry; không nạp toàn bộ catalog
   cho task hẹp và không coi nó là blacklist.

Không phát hành status report hoặc bắt đầu meaningful run trước khi hoàn thành
chuỗi trên trực tiếp từ workspace hiện tại.

## Bất biến vai trò

- Owner giao intent/thesis; agent phải tự bổ sung market mechanism, alternative,
  risk, execution và phép falsify. Chỉ nói “input không đạt” rồi dừng là sai vai.
- Một kill đóng đúng tested object, không đóng goal. Sau valid failure: failure
  packet -> fresh search cell/ID hoặc blocker thật cần quyền mới.
- `NO LEGAL CANDIDATE` chỉ đóng boundary đã khai. Không dùng một prompt/lane để
  tuyên bố frontier toàn dự án hay goal complete.
- Báo cáo luôn phân biệt `engineering-valid`, `economic-valid` và
  `promotion/deploy-ready`; package/compile/PF in-sample không tự tạo edge.
- Không hứa lợi nhuận, không bịa track-record. Capital preservation trước growth.
- Build/fix/complete phải tự đi vòng an toàn đến economic verdict/delivery hoặc
  blocker cần quyền mới; không chờ Owner nhắc từng bước.
- Closeout theo Two-Speed trong `validation_gates.md`: loser chạm gate đã khóa
  dùng Fast-Kill lean; survivor/continued candidate mới dùng Heavy-Delivery.

## Bản đồ canonical

| Câu hỏi | File |
|---|---|
| Mục tiêu book và DONE | `01. GOAL/GOAL.md` |
| Bản chất market, vai trò quant, hypothesis/overfit | `05. Playbook/research_doctrine.md` |
| Vòng brief -> probe -> build -> MT5 -> forensics | `05. Playbook/ea_golden_path.md` |
| Ngưỡng/evidence/hard invalidation | `05. Playbook/validation_gates.md` |
| Lệnh AlphaFactory chính xác | `05. Playbook/tool_runbook.md` |
| Chuẩn code MQL5/risk/execution | `05. Playbook/ea_engineering_standard.md` |
| Recent handoff (không phải authority) | `04. Memory/hot.md` |
| Hypothesis authority | `04. Memory/research/CANDIDATE_REGISTRY.jsonl` |

Harness duy nhất: `02. AlphaFactory/alpha.ps1`. Source canonical:
`03. EA Developer/<EA>/<EA>.mq5`. Archive `00. Old File/` không phải nguồn
compile/evidence. Không commit/push nếu Owner chưa yêu cầu rõ trong message hiện
tại.
