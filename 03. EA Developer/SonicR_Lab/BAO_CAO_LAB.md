# BÁO CÁO LAB — SONIC-LAB Round 2 (tiếng Việt)

Kính gửi anh,

Em đã chạy xong vòng nghiên cứu Python-only theo đúng brief: đọc spec,
dựng harness causal, freeze PREREG (sha256 đã ghi log trước khi tính bất
kỳ P/L nào), census outcome-blind, DESIGN sim 17 configs × 2 symbols,
100-seed controls, multiple-testing, MC drawdown. VALIDATION không chạy
vì không config nào đủ điều kiện vào — HOLDOUT vẫn niêm phong tuyệt đối.

## 1. Kết quả một câu

Không có variant nào vượt qua gate D5 (PF x1 ≥ 1.20 + PF x1.5 ≥ 1.05 +
≥1 lệnh/tuần + ≥60% năm dương + thắng random ở p95). Nhưng family F2
Nhất Hoài là cái duy nhất có tín hiệu thật — thắng 100/100 random seeds
trên EURUSD và 96/100 trên XAUUSD — chỉ là kinh tế chưa đủ mạnh.

## 2. Parity với run 16/08

- PF tái lập được trong tolerance (0.86–0.91 so với 0.94). N không tái
  lập được chính xác (artifacts run cũ đã bị xóa, feed khác) — gần nhất
  là interpretation B (W2 gate ON): N=364 vs kỳ vọng ~270.
- Kết luận: J ngày 16/08 rất có khả năng đã bật gate "wave xuất phát tại
  vùng S/R" — điều mà source code hiện tại chỉ còn là telemetry. Bằng
  chứng chi tiết trong PARITY_J.md.

## 3. Census — bao nhiêu tín hiệu mỗi tuần

- J base: ~2.0 tín hiệu/tuần/symbol.
- Các gate ladder: W2 cắt 80–85%, W3 cắt ~58%, W4 (angle ≥0.05) cắt 97%
  (gần như giết chết), PVSRA-agree cắt 98% (chết).
- F2 Nhất Hoài: ~7–8 tín hiệu/tuần/symbol — đúng kiểu doctrine Sonic.
- F3 Lucy ~15–21/tuần, F4 Bai14 ~17/tuần — nhiều nhưng thua tiền.

## 4. DESIGN — con số chính

| variant | EUR PF x1/x1.5 | XAU PF x1/x1.5 | lệnh/tuần |
|---------|----------------|----------------|-----------|
| F0_J (16/08) | 0.90 / 0.87 | 0.79 / 0.70 | ~1.1–1.2 |
| F1 tốt nhất (W2swing) | 1.08 / 1.05 | 0.57 / 0.51 | ~0.3–0.6 |
| F2_NH_b | **1.15 / 1.12** | **1.05 / 0.99** | ~2.5–2.8 |
| F3_LUCY_a | 0.86 / 0.79 | 0.64 / 0.49 | ~8–9 |
| F4_BAI14 | 0.97 / 0.93 | 0.82 / 0.73 | ~5.5–6 |

Điểm đáng chú ý: F1_W4a đạt PF 1.20–1.49 nhưng chỉ ~18–22 lệnh trong 10
năm — không đánh giá được (và nằm gọn trong phong bì max-PF của random:
p50=1.72). Cadence thực tế không config nào chạm band GOAL 10–40
lệnh/tuần/symbol ngoại trừ F3/F4 — mà hai cái đó thua tiền.

## 5. Ladder anatomy — yếu tố nào thật sự đẩy PF

- **W2 swing-zone (wave xuất phát trong vùng S/R)**: +0.18 PF trên EUR.
- **W3 leg-1 xuyên Dragon**: +0.16 PF trên EUR.
- **W4 Dragon angle ≥0.05 ATR/bar**: +0.30 PF — gate mạnh nhất nhưng chỉ
  còn ~2 lệnh/năm.
- R1b/R2a (stop/target mới): +0.04–0.05 — nhỏ.
- R2b (target WHQ ≥1R): **−0.11** — làm hỏng, vì target WHQ quá xa so với
  sóng ngắn.
- PV (PVSRA-agree): giết cadence, không đánh giá được.
- Trên XAUUSD: mọi element đều âm so với EUR — Classic không dịch sang
  vàng.

→ Câu trả lời cho câu hỏi "5 element còn thiếu có tạo edge không": CÓ
tín hiệu thật (W2 swing-zone + W3 + W4 đều đẩy PF đúng hướng), nhưng từ
base ~0.90 quá thấp nên chưa đủ để qua gate.

## 6. Phân tích F2_NH_b — tại sao dương mà chưa đạt

- Median lệnh: −1.02R; mean: +0.004R → kiếm tiền nhờ đuôi phải (37% win,
  lệnh thắng chạy median +2.3R).
- Lệnh thua trung bình đã chạy +0.61R thuận chiều trước khi chết — tín
  hiệu đẩy giá đúng, nhưng exit trả lại phần lớn.
- 22% lệnh bị Friday-flatten đóng (không theo plan).
- MC P95 maxDD = 196R (EUR) / 79R (XAU) — vượt ngân sách 30R của prereg
  ngay cả khi PF đạt. Chuỗi "thua nhỏ liên tục, thắng lớn hiếm" tạo DD
  sâu theo cấu trúc.

## 7. Đề xuất bước tiếp cho Lead (không bỏ Sonic — theo đúng rule)

1. **Rẻ nhất & hứa hẹn nhất: redesign exit cho F2_NH_b.** Signal có
   thông tin thật (pct 100/96), loser chạy +0.6R trước khi chết → test
   trong prereg mới: (a) BE tại +0.5R + TP cố định 1.5–2R; (b) TP 1.5R
   thay zone; (c) time-stop sau 8 bar nếu MFE < 0.5R. Mỗi cái chỉ là một
   dòng tham số trên cùng signal stream.
2. **J composite tối thiểu**: J + W2swing + W3 (bỏ W4/PV vì chúng giết
   cadence). Nếu hai element stack được, PF kỳ vọng ~1.2–1.4.
3. **F2_NH_b + H1-context filter** cho XAU (PF 1.05, pct=96 — mechanism
   chạy được nhưng cost plane 5.5p/lệnh ăn mất edge).
4. Ghi chú anomaly (KHÔNG phải Sonic): trigger Classic tại WHQ-gate trên
   EURUSD khi đảo chiều cho PF=1.18 — một family "fade WHQ breakout" đáng
   probe rẻ, nhưng là hypothesis mới tách biệt.

## 8. Những điều chưa chắc

- N parity không khớp tuyệt đối → spec J ngày 16/08 có thể còn 1–2 chi
  tiết nhỏ khác (w của W2 band, max_pullback_age). PF khớp nên ảnh hưởng
  kinh tế nhỏ.
- PVSRA-agree và W4 chưa đánh giá được vì cadence gần 0 — không kết luận
  chúng vô dụng, chỉ là "không đủ data trong spec này".
- Suspect bars ~30–38% trên đoạn hcc pre-2010 (chỉ dùng cho parity);
  DESIGN trên lab cache ~12–18% suspect exits — clean-PF sai khác <0.01.

## 9. Trạng thái artifact

PREREG hash không đổi; 17 configs, không thêm config nào sau freeze;
HOLDOUT không bao giờ load (loader raise + grep được); trades CSVs trong
out/; LAB_LOG UTC đều đặn.


---

# PHẦN 2 - VÒNG 2 SỬA LỖI + VÒNG 2B (tối 23/09, tiếng Việt cho anh)

## 1. Dữ liệu bị lỗi gì?

Hai lỗi thật, cả hai đã được reviewer/Lead tìm ra:

1. **Bar giả trong giờ rollover.** Nguồn M1 có ~1% bar "suspect" (đánh
   dấu sẵn trong feed), tập trung ở khung 00:00–00:20 giờ server của
   EURUSD và 01:00–01:20 của XAUUSD. Đo lại đúng cách (test đầu tiên
   của Lead dùng median nên không thấy): trong cửa sổ này, số lệnh
   THOÁT ra nhiều gấp 19–450 lần so với tỷ trọng thời gian lệnh ở đó;
   biên độ bar max mỗi ngày trong cửa sổ gấp trung vịnh 31 lần (EUR) /
   38 lần (XAU) hai cửa sổ yên tĩnh kế bên; và 25.7% ngày EUR / 18.1%
   ngày XAU giá "nhảy > 0.5×ATR rồi quay về trong 30 phút" — đường giá
   bịa, không phải giá thật. Một ngày chỉ có ~1–2 bar cực trị nên
   median không bắt được.
2. **Stop-loss sai phía / quá nhỏ.** `sl_big_swing` có thể trả về đỉnh/
   đáy sai phía lệnh → một lệnh từng ghi −154R ảo. Đã sửa tận gốc
   (chỉ lấy swing confirmed đúng phía, không có thì bỏ lệnh) + guard
   trong sim. Thêm sàn E2: |pending − SL| phải ≥ max(3× phí round-trip,
   0.15×ATR14) — loại đúng 759–6866 lệnh micro-stop không khả thi trên
   XAU.

## 2. Đã thay đổi gì?

- Chạy lại TOÀN BỘ 25 configs × 2 symbols trên 2 harness: H0 (giữ bar
  suspect, có phí rollover tăng + sàn E2) và H1 (bỏ hẳn bar suspect).
  Metric chính đổi thành PF_R (lãi/lỗ tính theo R — đúng cách EA size
  lệnh theo % rủi ro), PF pips vẫn báo song song.
- Hand-check 30 lệnh trên cả 2 harness: 0 lệch.
- Round 2B chạy đúng spec LEAD_NOTE_4 (hash khớp), PREREG_V2 đóng băng
  TRƯỚC khi có bất kỳ P/L 2B nào.

## 3. Kết quả: chưa có gì qua gate, nhưng thấy được đường đi

| ứng viên gần nhất | PF_R H0 | PF_R H1 | lệnh/tuần | vì sao rớt |
|---|---|---|---|---|
| XAUUSD F5_S3 | 1.40 | 1.64 | 0.15 | quá ít lệnh (~7/năm) |
| XAUUSD F5_S2 | 1.15 | 1.38 | 0.51 | ít lệnh + PF<1.20 ở H0 |
| EURUSD F2_NH_b | 1.17 | 1.19 | 2.5 | PF<1.20 + năm dương chỉ ~25% |
| EURUSD F1_W3 | 1.08 | 1.19 | 0.52 | PF + ít lệnh |

**Không config nào đạt cả 2 harness → VALIDATION không đọc → HOLDOUT
vẫn niêm phong.** Em không chỉnh tham số để ép qua gate (rule cấm).

Phát hiện đáng giá nhất: **confluence score S** (đếm 4 yếu tố xác
nhận cùng lúc) cho dose-response dương có ý nghĩa thống kê trên cả 2
symbols và cả 2 harness (Spearman p=0.003–0.02) — càng nhiều yếu tố
đồng thuận, expectancy càng cao. Nhưng S≥3 chỉ cho ~7 lệnh/năm nên
chưa đủ mẫu để kết luận.

## 4. Đề xuất cho Lead (round 3, cần prereg mới)

1. **Nới S xuống ≥2 / bỏ 1 element yếu** để đạt ≥1 lệnh/tuần rồi đo
   lại — đây là hướng duy nhất có dose-response đo được.
2. **Sửa exit của F2_NH_b** (loser chạy +0.6R rồi chết — rò rỉ quản
   lý lệnh, signal vẫn có tin thật, pct=100 trên EUR cả 2 harness).
3. **Đăng ký sẵn variant "flat 23:50"**: bỏ qua giờ rollover tăng
   XAU F2_NH_b PF_R 0.93→1.04, F5_S3 1.58→1.67 — ăn đúng vào lỗi
   dữ liệu vừa đo được.


---

# PHẦN 3 - VÒNG 2C: KIỂM CHỨNG TRÊN 10 CẶP TIỀN MỚI (tiếng Việt cho anh)

## Câu hỏi

Các phát hiện round 2 (confluence dose-response, XAU F5_S3 PF_R 1.64,
EUR F2_NH_b 1.19) là thật hay là may mắn sau 100 ô thử? Cách kiểm sạch
nhất: chạy NGUYÊN rules đã đóng băng trên 10 cặp tiền chưa từng fit
(GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCAD, USDCHF, EURJPY, GBPJPY,
EURGBP, AUDJPY) — không đổi tham số nào, không đọc VALIDATION/HOLDOUT.

## Dữ liệu basket

- Cả 10 cặp đủ 100% tuần của DESIGN, không cặp nào bị loại.
- Lỗi rollover giống hệt EUR/XAU: ~1.1% bar suspect, cụm 23:59–00:30
  giờ server, biên độ cực trị gấp 19–28 lần cửa sổ yên tĩnh → vấn đề
  feed có thật trên toàn basket, harness H1 (bỏ bar giả) vẫn đúng.

## Kết quả kiểm chứng (đúng criteria đã prereg)

| tiêu chí | kết quả |
|---|---|
| R1 essence (Spearman S vs R) | **KHÔNG tái lập**: Stouffer p=0.26 (H0) / 0.44 (H1); rho quanh 0 trên 10 cặp → dose-response EUR/XAU là luck |
| R2 F2_NH_b (pooled PF_R≥1.10) | gần nhưng **trượt**: 1.05 (H0) / 1.06 (H1); >1.0 trên 9/10 cặp |
| R3 luck check F2_NH_b | **ĐẠT**: pooled PF_R thắng null ở percentile 100 cả 2 harness |
| F0_J, F5_S2, F5_S3 | fail cả R2 lẫn R3 — F5_S3 XAU 1.64 là đặc thù vàng |

## Ý nghĩa thực tế

- **F2_NH_b có edge thật trên toàn basket** (9/10 cặp >1.0, thắng null
  100/100 seeds) nhưng nhỏ hơn kỳ vọng EUR: ~1.06 thay vì 1.19 —
  con số EUR là đỉnh của phân phối, không phải mức trung bình.
- **Confluence S/PV/W4 không có thông tin** trên symbol lạ → nghỉ.
- **Ở cấp tài khoản** (12 symbols, cap 5 lệnh/tuần + tối đa 3 lệnh mở):
  F2_NH_b cho **5.0 lệnh/tuần, PF_R 1.11–1.17, năm dương 64–73%,
  MC DD P95 59–81R** — tốt hơn mọi single-symbol nhưng vẫn dưới gate
  1.20 và vượt ngân sách DD 30R.
- Chi tiết hay: cap 5 lệnh/tuần làm PF tăng 1.05→1.17 → các fill sớm
  trong tuần mang phần lớn edge.

## Đề xuất cho Lead (round 3, prereg mới)

1. F2_NH_b + filter chất lượng top-of-week (khi >5 signal xếp hàng thì
   chọn lệnh tốt nhất) — mechanism đo được, không phải tune.
2. Redesign exit F2_NH_b trên 12 symbols (loser vẫn rò +0.6R).
3. Bỏ hẳn nhánh confluence S/W4/PV — đã chết trên basket.


---

# PHẦN 4 - VÒNG 2D: QUẢN LÝ THOÁT LỆNH CHO F2_NH_b (tiếng Việt cho anh)

## Câu hỏi

Entry F2_NH_b đã chứng minh có edge mỏng nhưng thật trên 10 cặp lạ.
Vòng này chỉ đổi CÁCH THOÁT (entry, SL, TP, session, cost giữ nguyên
đóng băng): liệu một rule thoát tốt hơn có nâng hệ qua cổng PF_R 1.10
không?

## Đã thử 9 biến thể thoát (trên 7 cặp DESIGN, 2 harness)

- X0-DF: đóng hết lệnh lúc 23:50 hàng ngày (daily flat).
- X1: khi lệnh chạy +1R thì dời SL về hòa vốn (break-even).
- X2: chốt nửa lệnh ở +1R, nửa còn lại giữ TP cũ + SL về hòa vốn.
- X3: X1 + thoát khi M15 đóng dưới Dragon (EMA34 low).
- X4: như X3 nhưng BỎ hẳn TP (chạy tự do).
- Mỗi rule có bản HOLD và DF, cộng thêm cột pessimistic (giả định xấu
  nhất trong cùng 1 bar).

## Kết quả: KHÔNG biến thể nào đủ điều kiện → dừng đúng prereg

- Cặp trade-đôi với X0 trên cùng tập lệnh: mọi rule bảo vệ đều CẮT
  winner nhiều hơn cứu loser. Đúng là ~28% lệnh thua SL từng lên +1R
  trước, nhưng vùng +1R cũng là đường đi của winner — bảo vệ ở đó
  thua ròng -0.02 đến -0.23R mỗi lệnh.
- Daily flat 23:50 nhìn đẹp trên H0 (PF_R 1.20, cả 7 cặp đều tăng)
  nhưng đó là ẢO: trên H1 (bỏ bar giả quanh rollover) mean dR ÂM.
  Tức là "lợi ích" của daily flat chủ yếu là tránh được bar dữ liệu
  giả — không phải edge thật.
- Sự thật ngược với giả thuyết "giữ qua đêm tốn phí": bucket giữ
  >24h là bucket DUY NHẤT lãi (+1.00R trung bình H0); daily flat
  cắt đúng phần ăn tiền. Lệnh fill thứ 6 vẫn tốt nhất (+0.19R).
- Pessimistic column âm cho mọi candidate → không relax gì cả.

## Ý nghĩa cho EA

- Exit hiện tại của F2_NH_b KHÔNG phải chỗ yếu có thể sửa bằng
  BE/partial/dragon ở +1R — đừng code mấy thứ này vào EA.
- Vấn đề thật sự nằm ở DỮ LIỆU quanh rollover (spread/swap thật chưa
  đo được) — đây là việc round 3 nên đo trước khi nghĩ exit tiếp.
- Nếu muốn thử exit tiếp: hướng hợp lý duy nhất là time-stop bất đối
  xứng (thoát lệnh âm sau N giờ, để winner chạy TP) — vì bucket <4h
  đang lỗ -0.54R còn bucket dài đang lãi. Cần prereg mới.

## Trạng thái dữ liệu

- Tập CONFIRM (5 cặp) chưa hề mở cho variant nào — file P/L variant
  của C không tồn tại.
- VALIDATION chưa đọc, HOLDOUT còn niêm phong.
- Mọi kiểm tra T1-T5 đạt: X0 qua code mới tái lập y nguyên file 2C
  (24/24 ô, sai số 0), handcheck 16/16 lệnh quản lý đúng cả 2 harness.

## Round 2E — Lọc lệnh theo đồng thuận trend đa khung (2026-09-23)

Round này hỏi một câu duy nhất: lệnh F2_NH_b nào có trend lớn cùng
chiều thì có lãi hơn không? Em chấm mỗi lệnh một điểm S_T từ 0 đến 3 —
ba thành phần: trend M15 (EMA34 so EMA89), Dragon H1, và trend H4.
Điểm đã được tính trước khi xem kết quả lãi lỗ, đúng quy trình prereg.

**Kết quả: không có đồng thuận trend = không lãi hơn.** Bảng pooled D:

| S_T | n (H1) | PF_R H1 |
|----:|-------:|--------:|
| 0 | 2849 | 1.075 |
| 1 | 1825 | 1.101 |
| 2 | 2079 | 1.128 |
| 3 | 1548 | **1.006** |

Lệnh đồng thuận đủ 3 khung lại là nhóm TỆ NHẤT — ngược hẳn giả thuyết.
Hệ số b = -0.007 trên H1 (không dương). Cắt lệnh ở c=2 (giữ S_T>=2):
PF_R 1.077 so lệnh bị loại 1.085 — không cải thiện, null chỉ đạt
phân vị 43/100.

**Quyết định theo luật đã đóng băng: dừng sau giai đoạn design.** 4/5
cổng E1-E5 fail; tập C không mở, VALIDATION không đọc, HOLDOUT niêm
phong nguyên. Không nới ngưỡng, không đổi công thức.

**Ý nghĩa cho EA:** Sonic R dạy "chỉ đánh theo trend lớn" — nhưng với
entry kiểu NH_b thì điều đó sai: lệnh đủ trend thường vào trễ, đúng
lúc sóng đã chín. F2_NH_b thực chất là một kiểu breakout hơi ngược
trend. Gợi ý tiếp theo cho Lead: (1) thay lọc trend bằng lọc chất
lượng sóng hồi (độ sâu, số bar); (2) đo phí rollover thật rồi thử lại
exit; (3) gate theo nén/vỡ volatility.

Không tốn tiền thật, không cặp nào bị sờ dữ liệu validation/holdout.

## Round 2F — Chỉ vào lệnh buổi sáng London (2026-09-23/24)

Round này kiểm chứng ý tưởng cốt lõi của Sonic R: lệnh NH_b ra tín
hiệu buổi SÁNG London (7-12h) có lãi hơn lệnh buổi CHIỀU (12-16h)
không. Lead thấy hiệu tượng này trên nhóm D; em kiểm chứng trên nhóm
C (5 cặp chưa từng phân tích) rồi một lần duy nhất trên VALIDATION.

**Trước đó em sửa 2 lỗi:**
1. Lỗi DST: code đặt mốc đổi giờ UK trễ 1 tuần khi ngày mùng 1 tháng
   sau là Chủ nhật (ảnh hưởng 3-2012, 3-2018, 10-2015, 10-2020). Sửa
   xong, chạy lại toàn bộ file lệnh: mỗi symbol chỉ đổi ~1% số lệnh
   (đúng các tuần lỗi + hiệu ứng domino của luật 1 vị thế).
2. Lỗi nhìn-trước (Lead phát hiện): bộ máy swing-zone chỉ đi tới, gọi
   sinh lệnh lần 2 sẽ thấy swing tương lai. Sửa ở runner (reset engine
   mỗi lần sinh lệnh); test T6/T7 chứng minh kết quả cũ sạch.

**Kết quả trên C — hiệu ứng TÁI LẬP:** sáng London PF_R 1.098 vs chiều
0.921 (H1); chênh lệch +0.115R, cận dưới 95% = +0.038 > 0; thắng trên
5/5 cặp và 8/10 năm → K1-K3 PASS hết.

**Kết quả VALIDATION (đọc 1 lần, 2020-2023):**
- Dữ liệu sạch (H1, bỏ bar giả rollover): sáng PF_R 1.125, cả 12 cặp
  AM>1.0 ở 10 cặp, sep +0.163 với cận dưới +0.085 → đẹp.
- Dữ liệu thô (H0, giữ bar nghi giả): sáng PF_R **0.874**, kỳ vọng âm
  → V1 FAIL vì luật đóng băng yêu cầu pass CẢ 2 harness.

**Phán quyết: KHÔNG promote.** Hiệu ứng buổi sáng là thật trên dữ liệu
sạch nhưng đổ dấu trên dữ liệu thô ở năm 2020-2023 — đúng cái bẫy mà
luật "cả 2 harness" được dựng lên để chặn.

**Con số cho anh:** nếu chỉ xem dữ liệu sạch, EA chỉ đánh sáng London
trên EURUSD+XAUUSD: ~3.4-3.8 lệnh/tuần/tài khoản, PF_R 1.39 trên
validation, drawdown mô phỏng ~36R. 12 cặp có cap 5 lệnh/tuần:
PF_R 1.22, DD ~47R. Nhưng con số này chỉ đúng nếu bỏ được bar giả —
round 3 cần đo spread rollover thật để kết luận.

Cũng xin báo lỗi nhỏ trong báo cáo 2C: tuần của account-cap đã tính
từ thứ Năm (epoch) thay vì thứ Hai London — sửa lại thì capped PF_R
F2_NH_b là 1.02 (H1) chứ không phải 1.11; DD ~138R chứ không phải
~59-81R. Kết luận 2C không đổi nhưng biên độ trước đây đẹp quá mức.

## Round 2F — đính chính E0' (24/09): lỗi dữ liệu quyết định V1

**Chuyện gì xảy ra:** sau khi đọc kết quả, Lead phát hiện V1 fail trên
H0 chỉ vì **một cây nến giả**: EURUSD bị chốt lỗ ở giá 2.655 (EURUSD
không bao giờ tới 2.65 — nến ghi sai giây, giá thuộc "ladder rác"
0.42/0.68/2.65). Nến đó biến một lệnh thắng +4.4R thành lỗ -810R và
kéo toàn bộ PF_R H0 xuống dưới ngưỡng. Còn một nến giả nữa cho lãi
ảo +57.7R — gian lận hai chiều.

**Hai luật sửa:** Lead đề rule E0 đầu (>3% và quay đầu trong 15') —
em chạy thử thì thấy nó **đánh trúng cả sự kiện thật** (SNB 2015,
flash crash GBP 2016/JPY 2019/vàng 2021, Brexit/ECB) và >20 bar một
symbol nên em dừng báo cáo đúng backup plan. Lead rút rule đó, chốt
**E0' = chỉ void nến có timestamp lệch giây (malformed record)** —
luật theo định dạng, không dùng giá, không nhìn tương lai, không thể
đụng sự kiện thật. Quét 12 cặp 2010-2023: **15 nến malformed**
(EURUSD 6, GBPUSD 5, USDCAD 4), tất cả đã nằm trong danh sách suspect
nên H1 không đổi — E0' chỉ sửa H0.

**Kết quả sau sửa (provisional — không phải xác nhận):**

| chỉ số | trước sửa | sau E0' |
|---|---|---|
| V1 fixed H0 | PF_R 0.874 — FAIL | **1.145 — PASS** |
| V1 free H0 | 0.905 — FAIL | **1.163 — PASS** |
| V1 fixed/free H1 | 1.125 / 1.160 | không đổi (đã sạch) |
| V2, V3 | 10/12, sep +0.163 | giữ nguyên — PASS |
| PF_R AM H0 theo năm | 2020 sập vì nến giả | 1.33/1.02/1.11/1.13 |
| Portfolio EUR+XAU H0 | PF 0.507, DD 837R | **PF 1.342, DD 37R** |

Audit lệnh đổi: 7 lệnh trên toàn bộ 2 windows (giúp 4, hại 3 — hai
chiều, không gian lận): gỡ -810R, -233R, +57.7R, +132.2R ảo.

**Nghĩa là gì cho anh:** phán quyết "NOT VALIDATED" ban đầu hóa ra do
lỗi dữ liệu chứ không phải chiến lược. Trên luật E0' hợp lệ, V1-V3
qua cả 2 harness cả 2 mode — **nhưng chỉ là provisional**: VALIDATION
đã đọc rồi, kết quả sửa chỉ chứng minh nguyên nhân fail là data bug.
Muốn promote thật cần chạy HOLDOUT niêm phong với E0' đóng băng và
không sửa thêm gì nữa. Câu hỏi mở round 3: phần chênh H0-H1 còn lại
nằm gần hết trong nến đầu phiên/rollover (wicks thật hay giá ảo?) —
cần đo spread rollover thật.


---

## ROUND 2G (+A1G) — ĐỌC HOLDOUT DUY NHẤT (EURUSD + XAUUSD)

**Kết luận: EA KHÔNG ĐẠT trên dữ liệu chưa từng thấy (FAIL), tạm
thời chờ Lead check tick audit A — fail chỉ có thể đổi thành
FAIL-DATA, không thể lên PASS.**

Đây là lần đọc duy nhất trên 174 tuần chưa ai mở (17/05/2023 ->
18/09/2026), sau khi đóng băng luật chơi trong PREREG_V7.

### EA có kiếm được tiền không?

Có, nhưng quá mỏng và không đủ chắc:

- Gộp EURUSD + XAUUSD (mode FR, harness sạch H1): 548 lệnh, PF_R
  1.104, lãi ròng +39.1R trong ~3.3 năm — vừa đủ qua ngưỡng 1.10 ở
  mode FR nhưng **trượt ở mode FL (1.087)**.
- Khi bỏ đúng 1 lệnh thắng lớn nhất của mỗi cặp (2 lệnh), PF còn
  **1.041 < 1.05** — lợi nhuận nằm quá nhiều trong vài lệnh lớn.
- Drawdown mô phỏng xấu nhất 5% (MC DD P95) = **58R**, vượt ngưỡng
  cho phép 50R. Chỉ 2/4 năm (gồm năm lẻ) có lãi ròng.

### Từng cặp (mode FR, H1, phí thật x1)

- **EURUSD**: 303 lệnh, PF_R 1.052 (+10.2R) — đạt riêng lẻ nhưng
  rất mỏng; năm 2023 -1.8R, 2024 -4.7R, 2025 +16.4R, 2026 +0.3R.
- **XAUUSD**: 245 lệnh, PF_R 1.163 (+28.9R) — tốt hơn; 2023 -3.4R,
  2024 +18.3R, 2025 +16.9R, 2026 -2.9R. Lệnh long PF 1.46 nhưng
  short chỉ 0.93 (ăn nhờ trend vàng).

### Bao nhiêu lệnh / tuần, drawdown thực tế

- Khoảng **3.1 lệnh/tuần/tài khoản** (cả 2 cặp gộp lại).
- MC DD P95 ~58R nghĩa là: risk **0.5%/lệnh** -> chuỗi lỗ sâu ~**29%**
  tài khoản; risk **1%/lệnh** -> ~**58%** tài khoản. Mức này quá
  rủi ro để chạy thật ở 1%.
- Lãi ròng +39R trên 174 tuần ~ 11.7R/năm: risk 1%/lệnh chỉ ~**12%/năm**
  trước drawdown — không tương xứng với đuôi rủi ro.

### Điều thú vị phát hiện thêm

- Cap cố định của XAU (21.22 USD, tính từ vàng ~1.500-2.000 thời
  DESIGN) giờ chặn 84% tín hiệu năm 2026 (vàng ~4.300). Nhánh cap
  tương đối (median range 250 ngày) cho kết quả tốt hơn rõ rệt trên
  cùng window: PF 1.23-1.26, DD ~34R, 3-4/4 năm dương — **ứng viên
  forward-test sạch** (không được gate, đúng luật).
- Audit list 152 lệnh (spike/|R|>5) đã giao Lead check với tick MT5:
  nếu các lệnh THUA trong list không xác nhận được trên broker ->
  FAIL-DATA; không bao giờ nâng lên PASS.
- Trên harness sạch H1 không có lệnh nào bị flag spike — phần win
  TP đáng ngờ chỉ tồn tại trên H0 (wick rollover), đúng vùng câu hỏi
  mở của round 3.

### Chưa biết gì

- Tick-check của Lead trên 152 lệnh audit (đang chờ).
- Wick rollover trên H0 là spread thật hay giá ảo — câu hỏi round 3.
- Nhánh cap tương đối chỉ là số liệu báo cáo, chưa được kiểm chứng
  trên dữ liệu mới — cần forward test nếu muốn promote.
