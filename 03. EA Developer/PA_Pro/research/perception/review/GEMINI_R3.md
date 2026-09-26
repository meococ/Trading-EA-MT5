# GEMINI_R3 — G-REVIEW round 3: tt_view_v3 (TT-3 fade-broken) vs c3, R83 §83.8

**Status: NOT decision-bearing.** Everything below was run on 3.1 Pro. At ~14:30Z (message received mid-run) the Owner ordered (verbatim): "cứ dùng 3.8 flash mở rộng, cho tới khi thành công. cấm dùng pro 3.1 hay giảm cấp 3.8 flash vì nó ngu". The Pro verdicts below are kept as information only. Condition (ii) of R83 §83.7 must be re-run on **3.8 Flash + Tư duy mở rộng**.

## Sets
- `c3`: `_scratch/gr1`.
- `tt_view_v3`: `_scratch/gr2/tt_view_v3`, rendered at 14:20Z (G-KIT log). It is C-3 + trade_tags=1 with `TRADE_VIEW_HIDE` hidden. The 8 `box_broken` boxes are drawn faded and truncated at `exit_bar`, on 7 panels: 9.2b, 9.10c, 9.36c ×2, 9.42b, 9.48b, 9.52a, 9.57b.

## Tooling log (chronological)
| time (Z) | model | prompt | set / batch | result |
|---|---|---|---|---|
| ~14:12 | 3.8 Flash + Tư duy mở rộng | P3 = P2′ + legend line | c3 A | refused after ~2 min ("Tôi không thể trợ giúp về điều đó…"), app/4322317067a32d0d |
| ~14:16 | 3.8 Flash | P3 | c3 A | began answering, then replaced by the same refusal, app/84d911e31c396e3b |
| 14:17–14:30 (4 calls, in this order) | 3.1 Pro | P4 = P2 + legend line (the finance disclaimer dropped) | c3 A | answered, app/58b133424b664044 |
| 〃 | 3.1 Pro | P4 | v3 A | answered, app/926c8e1e56830930 |
| 〃 | 3.1 Pro | P4 | c3 B | answered, app/3ddebf7e62f8a665 |
| 〃 | 3.1 Pro | P4 | v3 B | answered, app/3bbc33b49ac8a70a |
| ~14:30 | — | — | — | **Owner order: Flash Mở rộng only, until it succeeds.** Pro and plain Flash are forbidden. Batch C was not run. |
| 14:31 | 3.8 Flash + Tư duy mở rộng | 1-image capability test (planned) | — | blocked: the Chrome window was hidden, so the upload menu does not open |

**P4 wording** (the same for both arms; batch ids substituted): "Kiểm tra chất lượng (QA) phần mềm vẽ chú thích hình học lên đồ thị chuỗi thời gian (dữ liệu lịch sử 2012). Mỗi ảnh: các thanh nến, đường trung bình màu xám, vạch đứng nét đứt = thời điểm cuối dữ liệu. Phần mềm vẽ: hộp, đường chéo, đường ngang (liền/đứt), elip, chữ T/F, dấu M/W (khoảng thời gian); hình mờ nét đứt màu xám nhạt là hộp đã kết thúc. Với mỗi ảnh (…): đánh giá ok / lỗi / lỗi-nặng; liệt kê từng hình vẽ sai: loại + vị trí (giờ, mức), sai gì (cắt xuyên thân nến, xuyên qua vùng đi ngang, cũ hoặc xa vùng cuối dữ liệu, hộp bao cả đoạn tăng/giảm mạnh, đường ngang bị cắt qua lại nhiều lần, quá nhiều hình), nên sửa thế nào; thiếu hình cần có thì nói."

## Informational verdicts (3.1 Pro + P4; verbatim answers in r3_*.txt, same folder)

| panel | c3 | tt_view_v3 | the reviewer's words on the changed objects |
|---|---|---|---|
| 9.10c | lỗi-nặng | lỗi | The big box is gone (it faded off-screen). Remaining: diagonals cutting bodies; a missing box at "now". |
| 9.11b | lỗi-nặng | lỗi-nặng | Unchanged: the diagonal cuts bodies; a level is crossed back and forth. |
| 9.17b | lỗi-nặng | lỗi | c3: "Hộp nét liền (04:30 - 12:15) … nên được chuyển thành dạng 'đã kết thúc' (nét đứt mờ) từ thời điểm giá bứt phá lúc 09:00". v3: that error is gone; one short diagonal and a missing current box remain. |
| 9.25a | lỗi | lỗi-nặng | No box_broken change on this panel. The v2/v3 hide set only removed objects, so this is reviewer variance. |
| 9.2b | lỗi-nặng | lỗi-nặng | Remain: crossed diagonals and a long "Ww" line. |
| 9.33c | lỗi | lỗi | Remain: an old diagonal; stray dashes. v3 asks for a trendline in the late rally. |
| 9.36c | lỗi-nặng | lỗi-nặng | c3: the box "bao trọn cả một nhịp giá xả mạnh". v3: **"hộp đứt nét màu xám nhạt ở lúc 13:30 - 15:00 rất tốt"** (fixed). It stays fatal because of the ellipse and a dashed level. |
| 9.40a | lỗi | lỗi-nặng | No box_broken change. Diagonal / "Ww" / F-level findings; reviewer variance. |

- **Tally (8 panels):** fatal c3 5, v3 5.
- **Fixed by v3:** the E5 box errors on 9.10c, 9.17b and 9.36c. The reviewer praised the faded, truncated box on 9.36c.
- **New fatals on panels where v3 changed nothing:** 9.25a and 9.40a. Single-run verdicts move by one class without any object change.

## Lead reading (informational)
- TT-3's fade/truncate fixes exactly the box errors it targets: 3 of 3 panels where a box was named in c3.
- The remaining fatals are lines, levels, ellipses and M/W spans: E1, E2, E4 and E6. They are not boxes.
- The per-panel verdict noise (±1 class with nothing changed) means an 8- or 12-panel single-run tally cannot separate arms that differ on 3 panels. R84 must fix the decision statistic: count only findings that name changed objects, or run repeats.

_Timestamp note: the per-call times above are approximate. The Lead read the clock at 14:15:xx and at 14:32:26; the exact call order is given by the chat ids. An earlier draft said "14:45Z" for the blocked step, which was wrong: it was 14:31Z._
