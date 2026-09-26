# GRADING_RUBRIC_V2 — Volman UPA (grounded in the book)

Dùng cho calibration grader V2 (VPA-B1 Phase 4). Nguồn: sách UPA bản dịch Việt
(tr. dẫn bên dưới) + các phát hiện adjudication của Lead (G2_LEAD_ADJUDICATION.md).
Rubric này **chỉ chấm từ ảnh chart**; người chấm không được mở file khác.

## Bối cảnh ảnh (cố định)
- 120 nến M5 EURUSD; **bar cuối cùng (viền đen) là bar quyết định**; không có bar
  nào sau nó được vẽ.
- Đường tím = **EMA25**. Đường teal đậm ngang = **barrier bị phá** (vòng tròn =
  các lần chạm). Đường nét đứt đậm = **mức stop-entry** (nằm trên bar cuối =
  lệnh mua; nằm dưới = lệnh bán). Đường chấm xám = các barrier khác đang hiệu lực.

## Nguyên tắc nền (tr. 87–90, 101, 130, 227, 233–234)
1. Giao dịch phá vỡ chỉ hợp lệ khi **thuận áp lực chủ đạo** — xác định trước hết
   bằng hướng dốc EMA25 và vị trí phần lớn bar so với đường trung bình (tr. 101).
   EMA25 còn hướng thì **không giao dịch ngược** (tr. 227).
2. Phải có **tích lũy động lượng (buildup)** trước phá vỡ; càng dày càng tốt,
   gợi ý tham khảo ≥4 bar trong cú nén (tr. 89–90, 103, 223).
3. **Signal bar** = bar chủ chốt đóng cửa tại/xuyên biên theo hướng phá vỡ;
   entry là stop order **1 pip qua đỉnh/đáy của signal bar**, tức cú phá vỡ tự
   kích hoạt lệnh (tr. 88, 95). Không mua trên bar giảm mạnh / không bán dưới
   bar tăng mạnh (tr. 96).
4. Hai mối nguy phải soát trước entry: **nam châm ngược** trên đường tới stop và
   **vật cản** trên đường tới target (tr. 155). Không vào lệnh khi điểm vào cách
   xa EMA25 (tr. 72, 118, 234).
5. Bracket tham chiếu **10 pip stop / 20 pip target (R:R 1:2)**; nếu vật cản còn
   cách target <14 pip thì bỏ lệnh; không hạ target dưới 10 pip (tr. 83–84, 167).
6. Tránh: ngược xu hướng mạnh; vào ngay tại đỉnh/đáy vùng range; thị trường hỗn
   loạn (phần lớn bar dài hơn trung bình); tin tức; giờ trưa/cuối phiên
   (tr. 129–130, 166, 234, 412–419).

## Thang điểm

### A — Volman-grade (sẽ vào lệnh)
- **Bias**: EMA25 dốc đúng hướng lệnh và phần lớn bar nằm phía thuận; cấu trúc
  đỉnh/đáy cao dần (mua) hoặc thấp dần (bán). Không counter-trend.
- **Barrier/pattern**: biên ngang (hộp/range) hoặc biên mô hình rõ, ≥2 lần chạm
  thấy được; bar cuối đóng cửa tại/xuyên biên theo hướng phá vỡ.
- **Buildup**: cụm nén chặt sát biên trước phá vỡ (bar nhỏ, biên độ co lại,
  chồng lấn; lý tưởng EMA25 ép giá vào biên), tối thiểu 2–3 bar, tốt hơn ≥4.
- **Room**: đường tới target ≥ **2R (~20 pip)** thông thoáng; không có
  barrier/cụm giằng co/vùng số tròn cản ngay trước mặt; không có nam châm ngược
  giữa entry và stop.
- **Entry**: mức stop-entry nằm sát ngay ngoài **signal bar** (bar trước bar cuối
  hoặc chính bar cuối nếu nó là bar đóng tại biên); entry không đuổi — không cách
  barrier quá ~5–7 pip.
- **Không chop**: không phải chuỗi bar chồng lấn rối (barb wire), không bar dài
  bất thường, không phải giữa vùng range không rõ biên.
- **Thời điểm**: trong phiên hoạt động (sáng EU/UK hoặc sáng Mỹ); không sát tin.

### B — Biên (có thể vào)
- Thiếu **đúng một** tiêu chí phụ ở mức nhẹ: buildup mỏng nhưng có; room
  1.5–2R; entry hơi xa biên (4–7 pip); EMA25 hơi xa nhưng hướng vẫn thuận;
  cấu trúc hơi lỏng. Không phản thesis.

### C — Không nên vào
Bất kỳ lỗi nặng nào:
- **Counter-trend**: phá vỡ ngược dốc EMA25 / ngược cấu trúc đỉnh-đáy.
- **Không có barrier thực** hoặc biên mơ hồ, không đủ 2 lần chạm rõ.
- **Chop/barb wire**: bar chồng lấn rối, wick dài loạn, bar dài bất thường
  (biến động tin), hoặc range không biên giữa chart.
- **Room bị chặn**: barrier/cụm cản/vùng số tròn nằm trong ~2R trước mặt, hoặc
  nam châm ngược ngay dưới entry (lệnh mua) / trên entry (lệnh bán).
- **Chase**: entry nằm quá xa barrier (>~7 pip) hoặc trên đỉnh một bar phá vỡ
  dài (mua đuổi), tương đương stop nằm ngoài hộp.
- **Không buildup** trước phá vỡ.
- **Vào tại cực trị range**: mua sát đỉnh range / bán sát đáy range khi không có
  cấu trúc đảo chiều hợp lệ.
- **Sát tin/giờ chết**: bar dài bất thường quanh 14:30 CET hoặc phiên trưa.

## Ghi chú chấm
- Nếu ảnh cho thấy mức stop-entry nằm **quá xa barrier** (dấu hiệu entry đuổi
  theo bar phá vỡ), hạ xuống C theo mục "chase" — đây là lỗi entry của detector
  hiện tại, không phải lỗi của chart.
- Khi phân vân giữa A và B: chọn B nếu chỉ một điểm yếu; giữa B và C: chọn C
  nếu điểm yếu nằm trong nhóm lỗi nặng ở trên.
- Lý do: 1 dòng, nêu tiêu chí quyết định (ví dụ: "counter-trend so với EMA25",
  "room <2R vì barrier chấm ngay trên entry", "buildup dày + EMA dốc lên + room rộng").
