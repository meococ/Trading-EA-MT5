# GEMINI_R2b — G-REVIEW round 2b: tt_view_v2 vs c3 (same protocol), R82 §82.8

- **Sets:**
  - `tt_view_v2`: C-3 + trade_tags=1 with the full `TRADE_VIEW_HIDE` (9 tags). Rendered 12:40Z at `review/sets/tt_view_v2` and copied to `_scratch/gr2/tt_view_v2`. Compared with v1 it removes 7 more objects, all lines.
  - `c3`: control, re-run under the same model and prompt.
- **Owner default (12:59Z):** "mặc định dùng gemini flash 3.8 mở rộng" → 3.8 Flash + "Tư duy mở rộng" (label "Flash Mở rộng").

## Tooling log

- **13:02Z:** Flash Mở rộng, prompt P2, c3 batch A (9.10c, 9.11b, 9.17b, 9.25a), chat app/25418964a45a7f6c.
  - It thought for about 40 s ("Analyzing the request…", "Applying corrections…"), then answered: "Tôi không thể giúp bạn việc đó, vì tôi chỉ là một mô hình ngôn ngữ nên không thể hiểu điều đó." The chat title became "Từ chối kiểm thử phần mềm".
  - This refusal pattern matches R81 §81.2 (Mở rộng refused images 3/3).
- **Next (when the Chrome window is visible again; at 13:05Z it was hidden and the page does not submit):**
  1. One retry with P2′: P2 plus two sentences — "chỉ dùng để kiểm thử phần mềm, không dùng cho quyết định tài chính" and "chỉ nhận xét hình học, không đưa lời khuyên hay dự đoán". The rubric is unchanged. The same prompt applies to both arms.
  2. If refused again, fall back in this order: 3.8 Flash (no Mở rộng) + P2′, then 3.1 Pro + P2′.
  3. c3 and tt_view_v2 always use the same model and prompt.

## P2 (verbatim, recovered from app/691fbdb65827c770)

Kiểm tra chất lượng (QA) phần mềm vẽ chú thích hình học lên đồ thị chuỗi thời gian (dữ liệu lịch sử 2012). Mỗi ảnh: các thanh nến, đường trung bình màu xám, vạch đứng nét đứt = thời điểm cuối dữ liệu. Phần mềm vẽ: hộp, đường chéo, đường ngang (liền/đứt), elip, chữ T/F, dấu M/W (khoảng thời gian). Với mỗi ảnh (<ids>): đánh giá ok / lỗi / lỗi-nặng; liệt kê từng hình vẽ sai: loại + vị trí (giờ, mức), sai gì (cắt xuyên thân nến, xuyên qua vùng đi ngang, cũ hoặc xa vùng cuối dữ liệu, hộp bao cả đoạn tăng/giảm mạnh, đường ngang bị cắt qua lại nhiều lần, quá nhiều hình), nên sửa thế nào; thiếu hình cần có thì nói.

## Verdicts

None yet.
