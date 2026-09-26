# RULEBOOK — UPA (Volman) machine-oriented

Mọi mục là paraphrase từ sách; số trong ngoặc = trang. "Đề xuất causal" là cách
chuyển thành điều kiện closed-bar cho EA, chưa phải code.

## 0. Hợp đồng chung (áp dụng mọi setup)

| Hạng mục | Sách | Đề xuất causal |
|---|---|---|
| Bar | EUR/USD M5; chart "một pip" để đỉnh/đáy khớp hộp (tr. 88) | M5 Bid OHLC đã đóng |
| EMA | EMA25 (18–30 chấp nhận) (tr. 47) | EMA25 chuẩn |
| Áp lực chủ đạo | Dốc EMA25 + phần lớn bar một phía; EMA còn hướng → cấm ngược (tr. 101, 227) | `trend_d = d*(EMA_t − EMA_{t−6})/ATR_t ≥ 0.10` **và** ≥60% của 10 bar gần nhất đóng phía thuận EMA |
| Barrier | Đường/hộp qua nhiều lần chạm; chỉnh khi có đỉnh/đáy giả (tr. 51, 76) | Touch-cluster từ pivot đã xác nhận (T_min≥2, eps=0.10×ATR) |
| Signal bar | Bar chủ chốt đóng tại/xuyên biên theo hướng phá vỡ (tr. 88, 95) | Bar cuối trước trigger; `d*(close−B) ≥ −0.05×ATR`; không ngược thân mạnh |
| Entry | Stop order 1 pip qua đỉnh/đáy **signal bar** (tr. 95) | `entry = high_signal + 1pip` (long) / `low_signal − 1pip` (short); hiệu lực V bar; hủy nếu phá invalidation |
| Stop | 10 pip, đặt trong hộp nếu được; SL là market order (tr. 83, 95, 103) | Fixed 10 pip (DR1: [8,16]); không BE/trailing baseline |
| Target | 20 pip (1:2); nam châm; nếu vật cản chỉ để lại <14 pip lợi nhuận từ entry → bỏ (tr. 83, 167) | Fixed 2R; room gate ≥2R |
| Thoát thủ công | News exit; resistance exit (định trước); reversal exit (tr. 162–175) | Baseline: không (chỉ safety flat); DR-later: deterministic variants |
| Rủi ro | ≤2%/lệnh; % cố định (tr. 404) | 0.5% (research), 4%/8% locks |

## 1. Pattern Break (PB) — tr. 87–110

- **Preconditions (causal)**: barrier locked trước đó (≥2 chạm); giá tiếp cận biên
  với buildup nén; break bar đóng cửa vượt biên ≥0.05×ATR; thuận trend.
- **Buildup (sách)**: 4 bước lý tưởng: áp lực → phòng thủ → giằng co co lại sát
  biên → phá vỡ; chấp nhận "bẩn" (nhiều lần thử, chạm lại trong hộp); gợi ý ≥4
  bar (tr. 89–90, 103).
- **Signal bar**: đóng tại biên, hướng thuận; KHÔNG bán dưới bar tăng mạnh / mua
  trên bar giảm mạnh; bar quá dài làm stop nằm ngoài hộp → kém (tr. 95–96, 103).
- **Entry**: stop 1 pip qua signal bar; không front-run; chỉ fire khi bị vượt
  (tr. 95).
- **Stop**: 10 pip; lý tưởng nằm trong hộp để cú retest không quét (tr. 103).
- **Target**: 20 pip hoặc nam châm trước; kháng cự có thể xuất hiện 1 pip trước
  target (tr. 99).
- **Skip**: thiếu buildup; ngược trend; entry cách xa EMA25; sát vùng số tròn
  đang giằng co; thị trường "đứng yên" vô nghĩa (tr. 96, 101–107, 126).
- **Discretionary cần định lượng**: "buildup đủ dày"; "bar quá dài"; "quá xa EMA25";
  "biên đủ mạnh".

## 2. Pattern Break Pullback (PBP) — tr. 111–123

- **Ba biến thể**: (A) hồi về trendline đã phá; (B) mắc kẹt ngoài trendline vừa
  phá; (C) chững tại vùng sắp phá với trendline xuyên buildup (tr. 123).
- **Preconditions**: một phá vỡ đã xảy ra; giá hồi 50–60% sóng phá vỡ (hoặc giằng
  co ngoài trendline); vẫn thuận trend.
- **Signal bar**: bar đảo chiều tại đỉnh/đáy sóng hồi, đóng dưới/trên EMA25 theo
  hướng lệnh; ưu tiên bar chạm cả biên mô hình lẫn EMA25 (tr. 114–116).
- **Entry**: stop order dưới đáy/trên đỉnh signal bar; stop sau cấu trúc sóng hồi
  (nới vài pip nếu signal bar dài) (tr. 114).
- **Target**: nam châm kế tiếp (vùng số tròn cách ~20–25 pip là đẹp); R:R ≥2:1.
- **Skip**: sóng hồi quá mạnh (~100% với bar sức mạnh liên tiếp); entry cách xa
  EMA25; bối cảnh range mất cấu trúc (tr. 117–118).
- **Discretionary**: "hài hòa" giữa sóng hồi và sóng phá vỡ; mức nới stop.

## 3. Pattern Break Combi (PBC) — tr. 124–140

- **Preconditions**: một **strong bar** (thân ≥0.35×ATR, CLV≥0.5, đóng gần cực)
  ngay trước một **inside bar** (nằm trọn trong strong bar; lý tưởng cùng màu,
  nửa thuận của strong bar); tốt nhất trong một cú phá vỡ mô hình lớn hơn.
- **Biến thể**: hai doji dài; doji thay inside bar; combo 3 thanh (2 inside bar);
  **combi nghịch đảo** (inside bar trước strong bar — xác nhận đỉnh/đáy giả).
- **Signal bar**: inside bar (hoặc thanh cuối cụm).
- **Entry**: stop order 1 pip qua đỉnh/đáy inside bar (có thể chờ phá strong bar).
- **Stop**: dưới/trên đáy/đỉnh inside bar hoặc strong bar; dưới vùng hỗ trợ EMA25
  nếu inside bar tựa EMA (tr. 132).
- **Skip**: ngược trend; quá xa EMA25; nam châm ngược ngay dưới/trên; sóng trước
  đi lên từ đáy không chững (bẫy) (tr. 128–131).
- **Discretionary**: chọn vào tại inside bar hay strong bar; màu inside bar.

## 4. Pullback Reversal (PR) — tr. 143–160

- **Preconditions**: sóng chủ đạo rõ; sóng hồi **đầu tiên** kể từ phá vỡ; hồi
  **50–60%** (40% nếu trend rất mạnh + setup tốt); sóng hồi chạm/xuyên EMA25 rồi
  chững lại (gần như bắt buộc); lý tưởng có chạm kỹ thuật (trendline ext., đỉnh/
  đáy cũ, vùng số tròn) (tr. 143–145).
- **Buildup**: không bắt buộc 1 bar; thường ≥2–3 bar giằng co tại đỉnh/đáy sóng
  hồi; chờ cú phá vỡ **thứ hai** nếu nghi ngờ (tr. 145–147).
- **Signal bar**: bar đảo chiều tại cực sóng hồi (hoặc bar phá vỡ thứ hai).
- **Entry**: stop 1 pip qua signal bar (sell stop dưới đáy tại đỉnh sóng hồi; buy
  stop trên đỉnh tại đáy sóng hồi) (tr. 143, 147).
- **Stop**: trên đỉnh/đáy cụm đảo chiều (chặt); soát nam châm ngược tới stop.
- **Target**: nam châm/vùng số tròn (~25 pip); 20 pip chuẩn; <14 pip tới vật cản
  → thoát tại vật cản (tr. 146, 167).
- **Skip**: đảo chiều ngay lần chạm trendline đầu; sóng hồi là phần của mô hình
  đảo chiều lớn hơn (vai-đầu-vai); giá ở cực dưới/trên range mà vào tiếp; có tin;
  bar dài bất thường (tr. 145–151).
- **Discretionary**: "sóng hồi miễn cưỡng"; mức hài hòa; chọn bar 1 hay bar 2.

## 5. Trade-for-failure (TFF) — tr. 197–231

- **Preconditions**: một phá vỡ vừa thất bại (giá quay lại trong biên); lý tưởng
  là phá vỡ ngược **đầu tiên** khỏi EMA25 đang có hướng; có thanh đảo chiều mạnh
  xác nhận; xảy ra tại cú chạm lại đầu tiên với EMA25 của sóng chủ đạo.
- **Entry**: stop order ngược hướng phá vỡ thất bại, sau thanh đảo chiều (bán
  dưới thanh tín hiệu khi giá đã về dưới cạnh trên hộp; mua trên thanh tín hiệu
  ngược lại) (tr. 218, 226).
- **Stop**: ngoài cực thanh đảo chiều / ngoài biên hộp (tr. 233, 244).
- **Target**: nam châm thuận chiều; thoát tại điểm đảo chiều hoặc kháng cự.
- **Skip**: không phải phá vỡ ngược đầu tiên; hộp ở cực range/sát vùng số tròn
  đối kháng; thị trường hết xu hướng (tr. 228, 246, 263).
- **Discretionary**: "thanh đảo chiều mạnh"; thời điểm xác nhận thất bại.

## 6. Quản lý vị thế (tr. 161–196)

- **News exit**: thoát/không vào quanh tin; EUR/USD nhạy 14:30 CET, nhẹ 16:00;
  tin EU 08:00/11:00; thoát trước tin hơn là ở lại (tr. 162–165).
- **Resistance exit**: mức thoát định trước (đáy/đỉnh của đỉnh/đáy trước, biên
  range, vùng số tròn, trendline ext.); **nếu vật cản chỉ để lại <14 pip lợi
  nhuận tính từ entry → bỏ lệnh**; không hạ target <10 pip; thoát khi thị trường
  còn mạnh (tr. 166–170).
- **Reversal exit**: M/W phá middle section; đỉnh/đáy giả; trendline xuyên; ưu
  tiên hoà vốn/1–2 pip khi đã đi xa entry; cẩn thận thiên kiến (tr. 175–196).
- **Thời gian**: không giữ lệnh nằm im cuối phiên/qua weekend (tr. 166); tránh
  trưa EU 12:00–14:00 (tr. 227) và NY 18:00–20:00 (tr. 273).

## 7. Biến động thấp (tr. 412–441)

- Giữ nguyên nguyên tắc; đổi chiến thuật: target 8–10 pip, stop ~8 pip (5–6 pip
  với scalper) — vùng tích lũy cao 4 pip → stop ~7 pip gồm false break + spread
  1 pip; lưới mức 20 (00/20/40/60/80), chú ý vùng 40–60; nhiều market + chia ca;
  mục tiêu tháng (tr. 413, 417–419).

## 8. Danh sách "discretionary judgement" cần định lượng (ưu tiên cho DR1)

1. "Buildup đủ dày/hài hòa" — cần định nghĩa số bar/tỷ lệ.
2. "Entry cách xa EMA25" — cần ngưỡng ATR.
3. "Nam châm ngược/vật cản trong 2R" — cần định nghĩa mức (pivot/congestion/round).
4. "Sóng hồi miễn cưỡng/hài hòa" — cần thước đo độ dốc/độ dài bar.
5. "Bar quá dài/bất thường" — cần ngưỡng ×ATR.
6. "Biên đủ mạnh" — cần số chạm + recency.
7. "Chọn entry tại inside bar hay strong bar" — cần rule cố định.
8. "Cú phá vỡ thứ hai" — cần định nghĩa thời hạn.
9. "Thị trường đứng yên vô nghĩa" vs buildup — cần phân biệt định lượng.
10. "Sát tin/giờ chết" — cần cửa sổ phút.
