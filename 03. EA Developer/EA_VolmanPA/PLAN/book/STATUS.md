# STATUS — VPA-B1 (book extraction & DR1 groundwork)

Updated: 2026-09-20 (all phases complete)

| Phase | Trạng thái | Ghi chú |
|---|---|---|
| 0. Môi trường + route | DONE | Route **HYBRID vision-primary + OCR search index**. EasyOCR `vi` CPU cài xong (torch 2.14+cpu); đo chất lượng trên 5 trang: đọc được nhưng sai dấu hệ thống (~85–92% ký tự) → chỉ dùng grep/index. Vision đọc ảnh chính xác (kiểm chứng trực tiếp tr. 80, 84, 227). |
| 1. Page map + render + OCR | DONE | Mục lục tr. 5; PDF page = printed page; ranh giới chương verify bằng ảnh (3/5/7/9/10/11). 447 trang JPG 150 DPI (vision) + 447 PNG 200 DPI + 447 file OCR text (index) trong `_private/`. |
| 2. Reader agents | DONE | 10 chunk song song (tr. 6–447), output `notes/ch01..ch10.md` (195–447 dòng/chunk). |
| 3. Synthesis | DONE | `UPA_SYNTHESIS.md`, `RULEBOOK.md`, `GRADING_RUBRIC_V2.md`, `GAP_VS_SPEC.md`. |
| 4. Neutral review | DONE | Reviewer độc lập: **29/32 (90.6%) VERIFIED**, 2 WRONG + 1 UNSUPPORTED → đã sửa + re-verify trực tiếp tr. 84, 227 → **32/32 (100%)**. Coverage 5/5 setup, quote issues 0. Xem `REVIEW_NEUTRAL.md`. |
| 5. DR1 spec | DONE (draft) | `research/VPA-DR1_SPEC_DRAFT.md` — chờ Lead duyệt; chưa code. |
| 6. Grader calibration | DONE | 2 grader mù trên 60 case Lead-blind; hash TRƯỚC khi mở grade Lead. Binary AC1 vs Lead: **G1 0.770, G2 0.606** → PASS (≥0.60 cả hai). Xem `PLAN/grading/CALIBRATION_V2.md`. |
| Blockers | — | Tr. 264 mờ không đọc được (đã thử 150/200 DPI, OCR rỗng); một số mơ hồ dịch thuật đã ghi trong notes; session timezone của chart gốc không ghi rõ. |
