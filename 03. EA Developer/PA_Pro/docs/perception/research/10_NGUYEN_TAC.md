# 10 NGUYÊN TẮC — Cách một tay chuyên "đọc" chart

Viết cho Owner. Ngôn ngữ ELI5: mỗi nguyên tắc nói **tay chuyên nhìn thấy gì**,
**engine hiện thực nó ở đâu** (DN / primitive), **ví dụ nào trong TUNE golden**
(panel id + file overlay `research/perception/golden/qa/<id>_v2_overlay.png`),
và **nền tảng** của nó là `EVIDENCE` (có nghiên cứu/đo lường) hay `PRACTITIONER`
(nghề của Volman/trường phái, chưa test định lượng).

Mọi ví dụ lấy từ TUNE golden v2 — 527 object đã audit (92.2% usable).
Panel giờ là CET (giờ sách). Số đo tham chiếu: `research/perception/golden/Q2_MEASUREMENTS.md`.

---

## 1. Chart sạch — gần như không có mực

**Tay chuyên thấy gì:** một chart 8–10 giờ chỉ có vài nét. Mực là kết quả của
quyết định ("vùng này đáng nhớ"), không phải trang trí. Khi không có gì đáng vẽ,
câu trả lời đúng là *không vẽ* — engine có output riêng cho chuyện đó.

- **Engine:** DN_SALIENCE — chấm điểm toàn bộ ứng viên, NMS + hysteresis +
  budget; mục tiêu ~3 object/panel, trần cứng ~9. `STAND_ASIDE` là một output
  hạng nhất, không phải lỗi.
- **Ví dụ:** panel `9.63c` — `research/perception/golden/qa/9.63c_v2_overlay.png`
  — cả buổi chiều ~10 giờ tape chỉ có 2 đường line (1 TL dài tới ~15:35 + 1
  pennant ngắn 14:25–15:05).
- **Nền tảng:** `PRACTITIONER` (kỷ luật vẽ của Volman) + số đo golden:
  median ~3 object/panel trong TUNE.
- **Đo được trên bar:** đếm object đang live tại bar t; nếu score của ứng viên
  tốt nhất < ngưỡng ink và panel đã đủ budget → không vẽ thêm.

## 2. Đỉnh/đáy chỉ "tồn tại" sau khi giá quay đầu đủ xa

**Tay chuyên thấy gì:** một cái đỉnh chưa bị phủ nhận chỉ là "ứng viên". Nó trở
thành pivot thật khi giá đi xuống một khoảng đủ lớn — đo bằng kích thước nến
trung bình (ABR), không phải số pip cố định.

- **Engine:** DN_SWING — state machine directional-change hai ngưỡng:
  micro θ₁ ≈ 0.8×ABR (sinh pivot micro), structural θ₂ ≈ 2–3×ABR (sinh pivot
  chính), sàn prominence ≈ 0.5×ABR. Tham số đo từ TUNE, có thể tune.
- **Ví dụ:** panel `9.36b` — `research/perception/golden/qa/9.36b_v2_overlay.png`
  — các đỉnh/đáy nối thành falling line đều là pivot đã confirm.
- **Nền tảng:** `EVIDENCE` cho cơ chế (directional-change có nghiên cứu định
  lượng, scaling law trên FX — RT4); `PRACTITIONER` cho ngưỡng cụ thể.
- **Đo được trên bar:** pivot đỉnh tại bar s chỉ được xác nhận khi tồn tại bar
  t > s với `high[s] − low[t] ≥ θ·ABR(t)` — dùng được cho mọi primitive khác.

## 3. Đi ngang là một cái hộp; cạnh hộp nằm trên "cụm" có đồng đội

**Tay chuyên thấy gì:** vùng giá bị kẹp giữa hai đầu là *tên* của một object.
Cạnh hộp được đặt nơi có ≥2 lần giá chạm cùng chỗ (đỉnh/đáy chụm nhau). Một bóng
nến lẻ loi vọt ra xa cụm **không phải cạnh** — nó là poke.

- **Engine:** DN_BOX — edge = cluster có company (≥2 chạm trong tolerance
  ~0.35×ABR); box_height = range của buildup trước break, không phải cực trị
  lông nến; giữ `build_start/build_end` tách khỏi span vẽ `t0/t1` (D9 audit).
- **Ví dụ:** panel `9.54a` — `research/perception/golden/qa/9.54a_v2_overlay.png`
  — hộp phiên Á 02:00–09:10 (~22 pips) + 1 rising line từ đáy 07:30; hai cạnh
  đều nằm trên cụm chạm nhiều lần, bài học của chart là cú tease vào số tròn.
- **Nền tảng:** `PRACTITIONER` (Volman + Darvas box + Wyckoff range cùng mô tả);
  cơ chế cluster `EVIDENCE` (lý thuyết cụm lệnh gần mức tròn — RT3).
- **Đo được trên bar:** tại bar t, đếm số pivot/đóng cửa nằm trong
  `edge ± tol` trên đoạn buildup; ≥2 → edge hợp lệ. TUNE: 111 box, median
  cao ~16 pips, buildup ~65 phút.

## 4. Bóng nến chọc qua cạnh rồi đóng cửa quay lại = cái bẫy (T/F)

**Tay chuyên thấy gì:** vượt cạnh *mà không đứng được* là thông tin mạnh nhất của
chart — nó nói phe kia còn lệnh phòng thủ ở đó. Volman đánh chữ **T** (tease)
khi hồi về trước break, **F** (false) khi hồi về sau break. Cả hai đều là poke
thất bại — 5 trường phái độc lập mô tả cùng một cấu trúc.

- **Engine:** DN_TF / primitive `POKE_REJECTION` + `LABEL_TF` — T/F là
  *attribute* gắn trên cạnh đang sống, không phải object riêng; dedupe để không
  sinh 200 nhãn. Containment chỉ tính trên **đóng cửa** trong
  `[build_start, build_end]` — bóng nến xuyên qua không phá hộp.
- **Ví dụ:** panel `9.1a` — `research/perception/golden/qa/9.1a_v2_overlay.png`
  — hai chữ T in ngay trên neckline dưới đỉnh đôi 07:15–07:45.
- **Nền tảng:** cơ chế `EVIDENCE` (order-clustering + stop-run mechanics, RT3);
  nhãn T/F và ngưỡng poke `PRACTITIONER`.
- **Đo được trên bar:** poke event = `high[t] > edge_top` (hoặc `low[t] <
  edge_bottom`) trong khi `close[t]` quay lại trong vùng; lớp T hay F theo việc
  poke xảy ra trước hay sau `build_end`.

## 5. Break thật thường có "buildup" ép sát cạnh trước khi phá

**Tay chuyên thấy gì:** break đáng tin hiếm khi đến từ xa — giá thường dồn ép
sát cạnh (một dải nến nhỏ nằm ngay dưới/trên cạnh) trước khi bật. Buildup là
"đối thủ đã hết lệnh phòng thủ" được viết bằng nến.

- **Engine:** DN_BOX — buildup gauge (thời lượng + độ nén sát cạnh, đo bằng bar)
  và break class {tease, false, proper} là causal-correlate thay cho các chỉ số
  `fwd_*` đã rút (Ruling 5b). Đây là correlate để *vẽ*, không phải dự báo.
- **Ví dụ:** panel `9.39a` — `research/perception/golden/qa/9.39a_v2_overlay.png`
  — hộp Á dài 01:10–08:35 chỉ cao ~11 pips (1.3146–1.3157); nến nhỏ ép sát đỉnh
  hộp từ ~06:50 rồi bật mạnh đúng lúc mở phiên Âu.
- **Nền tảng:** `PRACTITIONER` (Volman: "pressure buildup" là điều kiện lõi của
  setup). Đối chứng thống kê DR-MARKET còn provisional — không dùng làm
  provenance.
- **Đo được trên bar:** `buildup_len = build_end − build_start` (bar); nén sát
  cạnh = phần trăm bar cuối buildup nằm trong `edge ∓ 0.5×ABR`.

## 6. Squeeze = giá bị nén giữa hai bức tường đang co lại

**Tay chuyên thấy gì:** khi hai cạnh có tên (đỉnh hộp + đường dưới đáy, hoặc hai
đường) siết lại thành cái nêm, giá đang bị "bóp" — phá ở đỉnh nêm thường rất
quyết liệt. Squeeze là object hiếm (TUNE chỉ có 2) nhưng cực có thông tin.

- **Engine:** DN_SQUEEZE — cần **hai bức tường live có tên**, khe hở co dần theo
  bar, và giá ở gần đỉnh nêm. Nến nhỏ lòng vòng một mình *không đủ* — đó là
  sai lầm detection phổ biến nhất.
- **Ví dụ:** panel `9.39a` — `research/perception/golden/qa/9.39a_v2_overlay.png`
  — SQUEEZE 06:50–08:15 vẽ bằng hai đường hội tụ (golden vẽ line ngắn, không vẽ
  ellipse) kẹp giữa đỉnh hộp ~1.3157 và các đáy nhô lên, ngay trước cú bật 08:xx.
- **Nền tảng:** `PRACTITIONER` (Volman squeeze, Bollinger squeeze, Wyckoff
  creek). Cơ chế nén → expansion có `EVIDENCE` yếu (volatility clustering) —
  ghi nhận nhưng không thổi phồng.
- **Đo được trên bar:** `gap[t] = wall_top(t) − wall_bot(t)` giảm đơn điệu
  ≥ N bar và `gap[t] < gap[t−N]·(1−δ)`; điểm hiện tại cách apex < ε·ABR.

## 7. Cạnh bị phá không chết — nó được "mang theo" thành level

**Tay chuyên thấy gì:** khi giá phá một cạnh và đi xa, cạnh cũ vẫn được nhớ như
một level mỏng — thường đóng vai trò ngược lại (đỉnh cũ thành sàn, đáy cũ thành
nóc). Hộp thì chết; *giá* của cạnh sống tiếp.

- **Engine:** DN_LEVEL — `LEVEL_CARRIED`: frozen price = cạnh cũ, span mang theo
  độc lập với target; vùng level lệch phía poke (đo bằng độ sâu poke median);
  bị chạm nhiều lần → giảm decision weight, không nhất thiết xoá mực.
- **Ví dụ:** panel `9.23c` — `research/perception/golden/qa/9.23c_v2_overlay.png`
  — LEVEL_CARRIED nét đứt ≈1.3318 kéo tới ~17:35 — đúng chỗ giá bật lên ở mép
  phải hộp 14:50–17:35 (bài học: long khỏi base bị bỏ qua vì lao vào kháng cự nét
  đứt).
- **Nền tảng:** `PRACTITIONER` (support→resistance flip, 5 trường phái); cơ chế
  cụm lệnh còn tồn dư `EVIDENCE` trung bình (RT3). Kiểm chứng thống kê DR-MARKET
  provisional.
- **Đo được trên bar:** khi `close` phá edge_top của box ≥ τ·ABR và giữ ngoài
  ≥ k bar → sinh LEVEL_CARRIED tại giá edge; zone = `edge ± w` với w lệch phía
  poke (≈ 0.5×ABR phía poke, ~0.25×ABR phía kia).

## 8. Đường xiên vẽ từ điểm neo "có tên", men theo phía được bảo vệ

**Tay chuyên thấy gì:** trendline không phải đường fit qua mọi nến — nó nối các
pivot *có tên* (extreme trước chặng, cụm pullback), men sát phía đang được phe
mạnh phòng thủ. Line có hướng cứng: dưới đáy = bull, trên đỉnh = bear.

- **Engine:** DN_LINE / primitive `LINE_FIT` — anchor = hull pivot (không fit
  ink residue — lỗi v1); chọn line theo max-touch; freeze sau khi confirm;
  re-anchor chỉ khi alignment mới vượt hysteresis; đi xa line → demote score,
  không vội xoá.
- **Ví dụ:** panel `9.33b` — `research/perception/golden/qa/9.33b_v2_overlay.png`
  — rising line bắt từ spike-low có tên 08:35 → 11:55 (chân tam giác), falling
  line nối đỉnh 12:25→13:35, MINI_LEVEL ngang ở đỉnh flag ≈1.3036.
- **Nền tảng:** `PRACTITIONER` (line craft của Volman/Brooks). Giá trị dự báo
  của line *sau* điểm neo cuối là câu hỏi mở K2 — engine vẽ theo craft, không
  claim predictive.
- **Đo được trên bar:** line chỉ qua ≥2 hull pivot đã confirm (θ₂); touch =
  `|pivot_price − line(t_pivot)| ≤ tol`; max-touch wins; slope sign phải khớp
  hướng phòng thủ.

## 9. Chữ cái M / W / SHS = cùng một chỗ bị probe hai lần

**Tay chuyên thấy gì:** M là "đỉnh bị thử hai lần thất bại", W là đáy thử hai
lần, SHS là vai-đầu-vai. Đây là *một* cấu trúc: lần probe thứ hai không qua
được chỗ cũ → phe tấn công hết đạn. Engine vẽ nó như một BRACKET duy nhất trên
chuỗi pivot, không phải 4–5 object rời.

- **Engine:** DN_BRACKET — phát hiện M/W/Ww/Mm/SHS trên chuỗi pivot đã prune
  (θ₂-structural + micro inner turns cho "w"/"m"); gate relevance (đủ lớn so với
  ABR, hai đỉnh cân nhau, neckline sạch). BRACKET coverage golden hiện chỉ 36% —
  route này là lỗ hổng lớn nhất của candidate layer (Q2).
- **Ví dụ:** panel `9.66c` — `research/perception/golden/qa/9.66c_v2_overlay.png`
  — chữ "-M-" in trên đỉnh đôi 15:00–15:30; panel `9.1a` có "SHS" đầy đủ.
- **Nền tảng:** `PRACTITIONER` (Volman letter brackets; SHS kinh điển);
  "hai lần probe thất bại" chia sẻ cùng cơ chế poke `EVIDENCE` như nguyên tắc 4.
- **Đo được trên bar:** trên chuỗi pivot đã prune: |đỉnh₁ − đỉnh₂| ≤ tol,
  đáy giữa nông hơn đỉnh ≥ κ·ABR, span ≤ S_max bar → bracket {M}; neckline =
  level đáy giữa (đóng vai trò cạnh riêng).

## 10. Đồng hồ là một phần của cấu trúc — phiên Á là nền, tin tức là vùng cấm

**Tay chuyên thấy gì:** cùng một hình nến, ý nghĩa khác nhau theo giờ. Phiên Á
(00:00–08:00 CET) thường là balance chờ Âu; 14:30 CET là giờ tin Mỹ — vùng
quanh nó là "không đọc được", bóng nến khổng lồ sau tin là poke của tin, không
phải edge mới.

- **Engine:** DN_TF — `RANGE_OPEN` bọc phiên Á; news window gating (±15 phút
  quanh sự kiện lớn, CET) làm nguồn tick/hành vi riêng; clock model: sách =
  CET; feed cửa sổ BOOK 2012 = giờ Berlin (trùng CET, lệch 0); feed DESIGN
  2016–2021 = EET (CET = giờ server − 1h, lệch 12 bar M5) — Lead chốt (D3).
  Session là attribute causal, không dùng kết quả tương lai.
- **Ví dụ:** panel `9.15c` — `research/perception/golden/qa/9.15c_v2_overlay.png`
  — cú counter-spike bóng dài ~15:15 trong vùng sau tin rồi giá lắng thành hộp
  15:50–17:40 (bài học gốc: sau spike bạo, kèo short bị gác lại). Panel `9.54a`
  là ví dụ hộp Á kinh điển.
- **Nền tảng:** `EVIDENCE` cho nhịp theo giờ (volatility/activity theo session
  là kết quả microstructure vững — RT3); `PRACTITIONER` cho rule "đứng ngoài
  quanh tin" của Volman.
- **Đo được trên bar:** `session(t)` = hàm của timestamp CET; bar có
  `|t − t_news| ≤ 15 phút` → flag `in_news_window`; RANGE_OPEN mở lúc 08:00
  CET với biên = range Á đo được.

---

## Bảng tổng kết

| # | Nguyên tắc | DN / primitive | Panel | Nền tảng |
|---|-----------|----------------|-------|----------|
| 1 | Ít mực / STAND_ASIDE | DN_SALIENCE | 9.63c | PRACTITIONER + đo golden |
| 2 | Pivot confirm bằng θ·ABR | DN_SWING | 9.36b | EVIDENCE (cơ chế DC) |
| 3 | Hộp = cụm chạm có đồng đội | DN_BOX | 9.54a | PRACTITIONER + EVIDENCE (clustering) |
| 4 | Poke-thất-bại = T/F | DN_TF / POKE_REJECTION | 9.1a | EVIDENCE (cơ chế) + PRACTITIONER (nhãn) |
| 5 | Buildup sát cạnh trước break | DN_BOX | 9.39a | PRACTITIONER |
| 6 | Squeeze = nén giữa hai tường | DN_SQUEEZE | 9.39a | PRACTITIONER |
| 7 | Cạnh chết → level mang theo | DN_LEVEL | 9.23c | PRACTITIONER + EVIDENCE (cụm lệnh) |
| 8 | Line từ anchor có tên | DN_LINE / LINE_FIT | 9.33b | PRACTITIONER |
| 9 | M/W/SHS = probe hai lần | DN_BRACKET | 9.66c | PRACTITIONER |
| 10 | Giờ CET + news window | DN_TF / RANGE_OPEN | 9.15c | EVIDENCE (session rhythm) + PRACTITIONER |

*Lưu ý chung:* mọi con số "median/min" trích từ Q2_MEASUREMENTS trên TUNE v2
(527 object, 486 usable). Các chỉ số `fwd_range_60`, `fwd_move_60`,
`fwd_rng_pctile` đã bị rút (Ruling 5b, dùng dữ liệu sau thời điểm vẽ) — không xuất hiện
trong tài liệu này. Kết quả DR-MARKET là provisional, chỉ nhắc dạng
"provisional (DR-MARKET, under review)".

*Lead 16:58Z: sửa 2 lỗi dữ kiện — mô hình đồng hồ ở nguyên tắc 10 (feed BOOK 2012 là giờ Berlin, D3) và số hiệu ruling rút `fwd_*` (5b, không phải 6).*
