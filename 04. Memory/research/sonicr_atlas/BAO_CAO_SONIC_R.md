# BÁO CÁO SONIC R — bức tranh đầy đủ, đối chiếu nguồn gốc (round 1C — có thêm video bài giảng Việt)

*Lane SONIC-ATLAS, 23/09/2026. Mọi dòng sự kiện đều ghi mã nguồn [Sxx] theo `SOURCES.csv`. File kỹ thuật đầy đủ: `SONICR_ATLAS.md`, `INDICATORS.md`. Bản round 1B đã sửa các lỗi của vòng 1 (xem REVIEW.md).*

---

## 1. Sonic R là gì, ai tạo ra, trade theo triết lý gì

Sonic R là một hệ thống giao dịch **swing trên khung M15**, do trader Singapore tên Kyaw (nick "sonicdeejay") mở thread trên Forex Factory năm 2008 [S07][S18]. Kyaw lấy cảm hứng từ sách của **Raghee Horner**: một hệ moving-average thuần tuý thắng khi thị trường có trend nhưng chết khi sideway, nên ông thêm phân tích sóng giá, volume và hỗ trợ/kháng cự (S&R) [S07][S13]. Kyaw từng mô tả nó trong giai đoạn đầu là "hệ scalp 5M/15M lãi tốt" trước khi hệ chính thức chốt ở M15 swing [S18].

Định nghĩa nguyên văn trong manual: *"phương pháp giao dịch biến động giá giữa các vùng hỗ trợ và kháng cự, chạy trên chart M15; dùng một SÓNG giá tại vùng S&R để xác nhận setup, dùng indicator DRAGON để chọn điểm vào, dùng TREND để xác nhận đúng hướng, dùng S&R lịch sử để chọn điểm thoát"* [S10][S11].

Từ năm 2012, thành viên **traderathome (TAH)** trở thành người viết toàn bộ indicator chuyên nghiệp và codify giáo lý; năm 2013 ông thêm phần phân tích **PVSRA** (Price-Volume-Support/Resistance Analysis — phân tích giá, khối lượng, hỗ trợ/kháng cự) [S18]. Mục tiêu lợi nhuận theo tác giả: **50-400+ pip mỗi lệnh** — nguyên văn Kyaw: "You can earn 50 to 400+ pips on a trade" [post#1 qua mirror S10 — file S18 đã lưu không còn phần rules]. Giá có thói quen đi trong các swing 100+/150+/200+/250+ pip [S31]. Sonic R là hệ **BÁN tự động** về bản chất — phần quan trọng nhất (đọc PVSRA, chất lượng sóng) là phán đoán của con người, tác giả không đưa công thức máy [S18][S06].

## 2. Bộ indicator tích hợp (bản 2014 của TAH)

Template chuẩn 2014 gồm 6 indicator đánh số Sonic_1 đến Sonic_6 [S06][S38]:

**Sonic_1 Solid/Filled Dragon** — vẽ "con rồng": 3 đường EMA34 theo giá High, Close, Low tạo thành dải tô đầy; kèm tuỳ chọn hiện đường Trend [S06][S13]. Lane này đã khôi phục file `SonicR_Filled_Dragon_White.mq4` gốc (SHA256 khớp manifest tháng 5): code xác nhận EMA34 trên High/Low/Close (buffer 0-5) + EMA89 close (buffer 6-7); chu kỳ 34/89 viết cứng trong code, không phải input; **KHÔNG có code nào tính "độ dốc" — góc Dragon là quan sát bằng mắt** [S49, file dòng 129-138, 251-262]. Không repaint trên nến đã đóng; chỉ nến đang chạy thay đổi. Bản của mình `SNR_Dragon.mq5`: đúng công thức EMA34 H/C/L nhưng vẽ 3 đường rời thay vì dải tô đầy, và tách Trend ra riêng — **logic đúng, hình thức khác** [S46].

**Trend (EMA89)** — đường EMA89 giá đóng cửa, nằm trong cùng indicator Dragon [S26]. Đọc: giá trên EMA89 ưu tiên mua, dưới ưu tiên bán; vị trí EMA89 so với dải Dragon cho biết chất lượng trend [S11][S29]. `SNR_Trend.mq5` đúng công thức; màu theo độ dốc 3 nến là lựa chọn của mình (tham số gốc không có — gốc không tính slope) [S46].

**Sonic_2 PVA Candles** — tô màu nến theo volume. Nến **CLIMAX**: volume ≥ 2 lần trung bình volume của 10 nến TRƯỚC (không tính nến hiện tại), HOẶC tích (biên độ × volume) lớn nhất trong 10 nến trước — màu xanh lá (mua) / đỏ (bán). Nến **RISING**: volume ≥ 1.5 lần trung bình 10 nến trước — xanh dương / tím. Đã verify trên CHÍNH file canonical `Sonic_2_PVA_Candles_White_20140317.mq4` (Lead drop, hash khớp zip 03-17-2014): vòng lặp `j=i+1..i+10` [S51 dòng 201-213]. **Phán quyết: con số 150%/200%/10-nến/spread×volume là chính xác từ code của TAH** — packet 16/08 ghi "reconstructed" là SAI; chỉ có bản 2011 cũ hơn dùng tham số khác (20 nến, hệ số 1.38, tính cả nến hiện tại) [S39]. TAH tự ghi nhận trong code: định nghĩa climax lấy từ **BetterVolume_v1.4** — nguồn gốc VSA [S51 dòng 41]. Alert kêu khi nến đang chạy đạt climax [S01]. Port mình `SNR_PVA_Candles.mq5` + `SNR_PVSRA.mqh` khớp hoàn toàn logic này [S46].

**Sonic_6 PVA Volumes** — histogram volume ở cửa sổ phụ, tô màu y hệt quy tắc PVA [S02, Volumes-Suite.mq4 dòng 313-332]. Có thanh "phantom" mờ phía sau để dễ nhìn trên nền đen [S02]. Alert climax nên bật ở indicator này thay vì ở PVA Candles [S01]. `SNR_PVSRA.mq5` khớp logic [S46].

**Sonic_3 Trade Levels** — KHÔNG phải chỉ báo S&R, và (sửa nhận định cũ) bản Feb-2014 KHÔNG đọc lệnh thật: nó là công cụ kế hoạch lệnh **THỦ CÔNG** — trader tự gõ vào input tới 20 entry (EP_1..EP_20), 3 TP, 3 SL; indicator vẽ các đường + đường entry-trung-bình + nhãn lãi/lỗ và alert giá bid [S06][S50]. Việc hỗ trợ tới 20 entry cho thấy "chia nhiều lệnh nhỏ vào một vị thế" là cách chơi thật của một số thành viên — khác với "nhồi lệnh lỗ" bị cấm [S50]. Bản Mar-2014 (57KB) chưa đọc được. Mình chưa port (không ảnh hưởng logic vào lệnh).

**Sonic_4 Access Panel** — "dao quân đội": (a) panel góc: tên cặp+khung, spread, range trung bình ngày/tuần, swap, thời gian còn lại của nến, giá bid; (b) đồng hồ 7 múi giờ chọn được; (c) đường Ask/Bid; (d) **lưới mức giá WHQ**; (e) fibo tự nhiên trên range hôm qua; (f) pivot ngày/fibo + mid-pivot; (g) vạch range trung bình ngày/tuần RDH/RDL/RWH/RWL; (h) vạch chia ngày; (i) vline mở cửa phiên Á/Frankfurt/London/New York và đóng London [S03, Access-Panel.mq4 dòng 51-88].
  - **Phán quyết lưới whole/half/quarter (đã chốt)**: code vẽ các mức 00, 25, 50, 75 trong mỗi khoảng 100 pip — khoảng cách mặc định 25 pip, input `__Incr_Decr_Levels_Density` chỉnh thành 50/75/100 hoặc 12.5/6.25 pip; mức quarter mặc định CHỈ hiện tới M30 [S03 dòng 948-980, 335-338, 101-115]. 1 "pip" trong code = `Point*10` (dòng 713) → trên vàng 2-số-thập-phân (Point=0.01) cùng một code vẽ quarter cách nhau **$2.50** (half $5, whole $10); trên feed 3-số vẽ $0.25 trừ khi tăng density. Độ quan trọng: whole > half > quarter [S12]. **Port mình `SNR_SRLevels.mq5` DIVERGE**: đang vẽ lưới input 10/5/2.5 pip, không phải lưới 25-pip cố định của bản gốc [S46].

**Sonic_5 FFCal Panel** — hiện tối đa 4 tin sắp ra trên lịch Forex Factory: giờ, tiêu đề, màu theo mức impact; ưu tiên tin high impact; có alert trước X phút [S04, FFCal-Panel.mq4 dòng 16-68]. Cố ý KHÔNG hiện số forecast/previous — theo TAH quan trọng là THỜI ĐIỂM tin, vì cá mập chuẩn bị trước tin [S04]. Đây là công cụ QUAN SÁT, không phải bộ lọc cấm trade [S04][S17].

**Các indicator thời kỳ đầu (trước PVSRA)**: TRO_Tunnel_Dragon (tổ tiên Dragon), QQE_Alert_MTF_v5, Sonic CCI 63, Normalized Volume Oscillator, PivotsDWM, SpudFibo, ZZ-Fractal, SHI_Channel_MTF [S27][S38] — bộ SonicRV3 ~2011, biến thể lịch sử hợp lệ.

## 2b. Cheat sheet — cài đặt anh nên có trên chart

| Indicator | Thông số gốc (từ code/manual) | Anh nên đặt | Lưu ý |
|---|---|---|---|
| Dragon (Sonic_1) | EMA34 High + EMA34 Close + EMA34 Low, dải tô đầy | đúng như gốc; KHÔNG chỉnh period | "góc Dragon" đọc bằng mắt, không có trong code [S49] |
| Trend | EMA89 Close | đúng như gốc | đường xác nhận hướng, không phải điểm vào [S49] |
| PVA Candles (Sonic_2) | avg = trung bình 10 nến TRƯỚC; rising ≥1.5×; climax ≥2× hoặc spread×vol max | đúng như gốc | màu chỉ là nhãn đọc-MM, không phải nút vào lệnh [S51] |
| PVA Volumes (Sonic_6) | cùng ngưỡng trên histogram | đúng như gốc | bật alert climax ở đây [S01][S02] |
| Access Panel (Sonic_4) | lưới 00/25/50/75 mỗi 100 pip; quarter ≤M30; density=0 | EURUSD/FX: mặc định; XAU 2-digit: code tự ra $2.50 grid | `SNR_SRLevels` của mình đang lệch (10/5/2.5) [S03][S46] |
| FFCal Panel (Sonic_5) | 4 tin sắp tới, màu impact, alert trước | đúng như gốc | công cụ quan sát, không phải news-filter [S04] |
| Trade Levels (Sonic_3) | gõ tay EP×20/TP×3/SL×3 | không bắt buộc | công cụ lập kế hoạch, không đọc lệnh thật [S50] |
| Khung | M15 lõi; H1 đọc bối cảnh; M5 chỉ cho scalping/entry sớm | M15 chính + H1 phụ | TAH: M5 "for scalping or earlier entry" — mất thời gian xác nhận [S08] |
| Phiên | London; tránh Á | London only cho Classic | TAH từng phá lệnh 1 lần vì setup đẹp — preference, không tuyệt đối [S08] |

## 3. Các setup: điều kiện, vào, cắt lỗ, chốt lời + ví dụ

**Classic (setup gốc, quan trọng nhất)** [S10][S11][S18]:
- Bối cảnh: giá đang ở một vùng S&R (mức whole/half/quarter, mức lịch sử, hoặc vùng tích luỹ) [S10][S12].
- Sóng: mua cần **L-H-HL** bắt đầu từ dưới Dragon; bán cần **H-L-LH** từ trên Dragon; tốt nhất nếu sóng chân 1 xuyên qua Dragon [S10][S11].
- Dragon phải dốc đúng hướng và giá nằm đúng phía; Trend (EMA89) xác nhận hướng [S10][S11].
- Phiên: **London** — nguyên văn TAH: "Classic entries are only recommend during the London session" vì lúc đó setup "phản ánh trend chính xác hơn và chạy xa hơn, thường vậy" [S08 — post TAH ngay trên #7679382, cùng trang 3756]. Câu "ENTRY SHOULD BE WITHIN LONDON SESSION" là cách cộng đồng diễn lại [S15].
- Trigger + vào lệnh: nến chân sóng 3 **đóng cửa thoát khỏi Dragon** → đặt stop-order cách nến đó "ít nhất vài pip". **Nguồn KHÔNG cho số cụ thể** — "several pips" là buffer tuỳ ý tránh bị quét bởi wick/spread; con số 3 pip trong spec mình là reconstructed [S10][S11]. Phía trước entry không được có S&R mạnh (đường chạy phải thoáng — "runway") [S15].
- SL: **bên kia đỉnh/đáy của swing giá LỚN gần nhất** — đỉnh/đáy cấu trúc của cả con sóng, không phải râu một nến [S11]; không quá 100-120 pip tính từ entry (EURUSD); cặp JPY khuyến nghị ≥80 pip [S31]; nguyên tắc "đủ rộng để giá thở" [S13].
- TP: mức S&R lịch sử — whole/half/quarter và giữa vùng tích luỹ [S10]; TAH thực hành thêm vạch RDH/RWH [S17].
- Quản lý: trail theo cấu trúc; đóng bất cứ lúc nào; không bao giờ nhồi lệnh lỗ [S10].

**Re-entry / Scout-trong-Classic** [S10][S08]: sau khi Classic chạy, pullback không phá cấu trúc → vào thêm gần đỉnh/đáy của nhịp hồi (hoặc khi giá phá qua high/low gần nhất, đường trước thoáng). Nhồi thêm khi Classic đang đỏ = KHÔNG được khuyến nghị (có thể là Stop Hunt của MM) [S08]. Đây là quản trị lệnh — timing và size mang tính tuỳ quyết.

**Scout** [S08]: vào sớm — hai dạng TAH mô tả (post 7679382, 16/08/2014):
- *Scout trước Classic*: PA kết thúc một nhịp mạnh hoặc đập liên tục vào S&R + volume hiện tại rất cao → khả năng đảo chiều/pullback lớn. Entry ngược trend giữa momentum — "rất nặng tính nhận thức", KHÔNG dùng Dragon để định vị (giá có thể đã xuyên qua). Rủi ro rất cao; chờ thêm xác nhận PA [S08].
- *Scout trong Classic* ≈ re-entry ở trên. Thứ tự an toàn: Scout-trong-Classic-đang-xanh < Scout-trong-Classic-đang-đỏ < Scout-trước-Classic [S08].
- M5: TAH cho phép "for scalping, or as an alternative for getting an earlier entry" — nhưng cảnh báo mất thời gian xem MM chuyển từ gom-sang-chạy; lõi hệ vẫn là "M15 Classic trong phiên London" [S08].
- PVSRA là phương pháp PHÂN TÍCH, không phải cách vào lệnh; cạm bẫy lớn nhất là dùng Scout/PVSRA để nhồi lệnh lỗ [S08][S10].

### Ví dụ mô tả từ nguồn (ảnh chart không tải được — chỉ có lời kể)

**VD1 — Classic bán chuẩn theo manual (post#1)** [S11]:
- Bối cảnh chart: giá đứng ở một vùng S&R phía TRÊN dải Dragon, khung M15 phiên London.
- Ba chân sóng: High → Low → Lower-High, khởi đầu phía trên dải; chân 1 xuyên xuống QUA Dragon (trường hợp "đẹp nhất" theo manual).
- Nến trigger: nến chân 3 đóng cửa hẳn dưới mép dưới của Dragon.
- Vào lệnh: sell-stop "ít nhất vài pip" dưới đáy nến đó; check trước không có S&R mạnh ngay phía dưới.
- Cắt lỗ: trên đỉnh của swing giá lớn gần nhất, xa nhất 100-120 pip tính từ entry.
- Chốt lời: mức S&R lịch sử phía dưới (whole/half hoặc giữa vùng tích luỹ).
- Kết quả: manual dùng ví dụ này để minh hoạ luật đặt SL; lệnh chạy theo hướng "run for profits" của MM.

**VD2 — Classic bán AUDJPY của chính TAH, 17/08/2014** [S08, trang 3756 thread]:
- Khung/phiên: M15 — vào lệnh **trong phiên Á**, TAH tự viết "setup đẹp nên tôi vào dù đang phiên Á".
- Đọc PVSRA: thứ Sáu trước bán mạnh; nhịp reset diễn ra trên volume giảm dần → dấu hiệu MM vẫn là phe bán; đỉnh cao nhất ngày in trên cột volume lớn nhất.
- Sóng + indicator: "một con sóng PA giảm đẹp, Dragon dốc xuống, giá nằm dưới Trend".
- Quản lý TAH nêu trước: TP có thể không tới trước phiên London; LS có thể kéo giá lên lại vì "các ngân hàng lớn muốn thêm lệnh bán" → có thể gỡ SL để thêm Scout; có thể hạ TP và giữ cho swing nhiều ngày.
- Bài học: ngay tác giả cũng coi phiên là preference chứ không phải veto tuyệt đối; PVSRA là lớp kể chuyện hướng đi; quản lý lệnh linh hoạt theo diễn biến.

**VD3 — Classic bị TAH chê (dạy học viên, trang ~3387)** [S15]:
- Chart: EURUSD M15, học viên vào Classic có sóng và đúng phiên.
- Lỗi: ngay phía trên entry là kháng cự mạnh "sát mặt", đồng thời trend lớn đang giảm — runway không thoáng.
- Bài học: "không có S&R mạnh ngay phía trước" là một veto thực tế được áp bằng mắt, không phải lời khuyên mềm.

**VD4 — Re-entry / Scout-trong-Classic** [S08][S10]:
- Chart: một lệnh Classic đang chạy và ĐANG XANH; PA hồi về hoặc vào dải Dragon.
- Sóng mới: một mini-wave 3 chân hình thành trong nhịp hồi.
- Điểm thêm lệnh: gần đỉnh/đáy của nhịp hồi; hoặc khi PA phá qua high/low gần nhất và phía trước thoáng.
- Có PVSRA: được phép thêm NGAY trong nhịp hồi thay vì chờ phá đỉnh/đáy cũ.
- Cấm: thêm lệnh khi Classic đang ĐỎ — khả năng cao là MM Stop Hunt.
- Tài liệu: PDF "Sneak Into Classic" của Gupito (21k lượt tải) dẫn checklist từng bước [S17].

**VD5 — Kết quả lệnh thật thread đăng (trang 3756)** [S08]:
- Catcher777: chốt Classic EU M15 "+2.800 pip × 2 tài khoản" ngày 15/08/2014 (có chart đính kèm).
- Patron: long GBPAUD M15 target 20-40 pip, đóng sớm vì kháng cự + double bottom + gap cuối tuần — quản lý tuỳ ý.
- santos23: đăng chart "Classic short for Monday".
- Bài học: thread thật cho thấy cả mục tiêu swing hàng trăm pip lẫn quyết định đóng sớm theo tay.

**VD6 — Scout trước Classic** [S08]:
- Chart: PA kết thúc một nhịp chạy mạnh, hoặc đập liên tục vào một mức S/R, kèm volume hiện tại rất cao.
- Đọc: khả năng đảo chiều (hoặc ít nhất pullback lớn) tăng → entry ngược sớm.
- Đặc điểm: entry theo nhận thức + xác nhận PA, KHÔNG dùng Dragon định vị (giá có thể đã xuyên qua dải).
- Rủi ro: cao nhất trong 3 dạng Scout — TAH khuyên chờ thêm xác nhận.

**VD7 — Cách dạy của cộng đồng Việt Nam** [S31][S33]:
- tamnhindautu dịch nguyên văn cơ chế: nến chân 3 phá Dragon → entry vài pip ngoài; SL ngoài swing gần nhất ≤100-120 pip; TP S&R lịch sử kể cả giữa vùng tích luỹ; cặp JPY SL ≥80 pip.
- Ví dụ VN thực hành: lệnh GBPJPY chốt +140 pip [S33].

**VD8 — Lệnh scalp vàng của Lucy (video, transcript qua NLM)** [S53]:
- Chart: XAUUSD; trend chính đọc trên H4/H1 đang tăng (giá trên các EMA); vào lệnh trên M15/M5/M1.
- Bối cảnh: giá hồi về test lại dải Dragon; một nến từ chối (pin/rút chân) in ngay tại dải.
- Vào: Buy ~1933 khi nến từ chối xuất hiện; SL 1930 ngay dưới râu nến; chốt chủ động trước khi sóng Elliott-5 hoàn tất.
- Kết quả: giá bật mạnh từ dải — thắng.
- Lưu ý: đây là kiểu *rejection-scalp* (khác trigger chân-3-đóng-cửa của gốc; SL theo râu nến chứ không phải swing lớn) — xem mục 6.

**VD9 — Ví dụ nhiễu "cầu vồng" nằm trong chính bài tamnhindautu** [S32 mục 5.6; S59 = cùng bài qua URL dup]:
- EURUSD H4, 6 EMA cầu vồng (6/12/18/24/30/36) + RSI14: ngày 1 EMA6/12 cắt lên + RSI 55 → ngày 2 hồi về EMA18 → Buy 1.1225, SL 1.1200 (dưới EMA36), TP 1.1300 (R:R 1:3), dời SL hòa vốn tại 1.1275 → chạm TP **+75 pip**.
- **Công thức này KHÔNG phải Sonic R** — không Dragon band, không sóng, không giáo lý S&R — nó nằm trong cùng bài viết như một phương pháp phụ.

**VD10 — Cách Nhật Hoài dạy vào lệnh (video, transcript qua NLM)** [S52]:
- M15 là tối ưu; M10/M5 được, **"không có nên đi xuống thấp hơn khung M5"** — khớp ranh giới M5 của TAH.
- Chờ nhịp hồi ĐẦU TIÊN quay về dải Dragon → vào khi một nến đóng cửa thoát hẳn khỏi dải (= trigger chân 3, trung thực).
- Hai kiểu SL ông đưa: chặt ngay ngoài cực trị nhịp hồi (ăn RR), hoặc rộng ngoài swing tích luỹ lớn nhất (ăn winrate — gần đúng luật TAH).
- TP vùng S&R gần nhất hoặc trail theo đỉnh/đáy mới + Pivot Point (điểm đỏ — phần ông thêm).
- Đây là giáo viên Việt gần cơ chế gốc nhất — chỉ thiếu PVSRA/WHQ trong video.

## 4. PVSRA — phân tích Giá-Volume-Hỗ trợ/Kháng cự

- Bản chất [S12][S18]: các thực thể đẩy giá ("MM"/cá mập) có thói quen — **phe mua thích kéo giá XUỐNG DƯỚI S&R quan trọng để gom, phe bán thích đẩy giá LÊN TRÊN S&R quan trọng để xả**. Xác định họ mua hay bán bằng cách xem phần lớn giao dịch (volume nổi bật) xảy ra ở đâu so với S&R chính.
- Đọc trên chart thực tế [S12][S31]: **"Xây dựng vị thế"** (position building): phe mua + giá đang giảm + các cột volume nổi bật nằm DƯỚI S&R/đáy = đang gom hàng (đừng vào — không biết họ gom bao lâu). **"Chạy để kiếm lợi nhuận"** (run for profits): phe mua + giá đang tăng + volume nổi bật vẫn dưới S&R ở các nhịp hồi = đang chạy lời — đây là lúc trade. Gương đối xứng cho phe bán (bán trên S&R/đỉnh). Nguyên tắc vàng TAH: **"không thể biết khi nào MM gom xong — tốt nhất chờ cơ hội trong pha chạy-lời"** [S31].
- Vai trò của nến màu PVA: màu chỉ đánh dấu NƠI volume nổi bật xảy ra để đọc ý đồ — không phải nút vào lệnh [S12][S18]. TAH: "PVSRA is a method of analysis, not a trade entry method" [S08].
- Giá hay đi trong các swing 100+/150+/200+/250+ pip — đây là thước đo vị trí giá trong chu kỳ [S31].
- Giới hạn tick volume: volume trên MT4/5 chỉ là số tick trên server broker, mỗi broker một số — chính thread thừa nhận [S16]; chỉ dùng như chỉ báo TƯƠNG ĐỐI (spike so với chính nó), không phải dòng tiền thật [S06]. TAH gợi ý chart M1 để nhìn hoạt động MM ở đỉnh/đáy theo thời gian thực [S31].

## 5. Kỷ luật và quản lý vốn theo tác giả

**Quy tắc 1 — không overtrade** [S10 — rules verbatim qua NLM cited_text của mirror; file S18 không còn rules list]:
- Không trade phiên Á; các setup đẹp nhất xuất hiện sau khi London mở.
- **Không quá 5 lệnh/tuần** — nguyên văn là khuyến nghị CHUNG cấp tài khoản trong danh sách quy tắc của post#1 ("You shouldn't trade more than 5 trades a week."), KHÔNG phải "mỗi cặp tiền 5 lệnh".
- Kyaw chủ yếu trade EURUSD nên trong thực hành của ông per-account ≈ per-pair; thói quen đa-symbol là của cộng đồng sau này.
- Tìm setup CHẤT LƯỢNG, không tìm số lượng.

**Quy tắc 2 — không nhồi lệnh lỗ** [S10][S18]:
- Tuyệt đối không averaging vào vị thế thua — kể cả khi PVSRA đọc rất đẹp.
- TAH cảnh báo riêng: sự xuất hiện của Scout + PVSRA chính là cám dỗ lớn nhất dẫn tới vi phạm quy tắc này [S08].

**Quy tắc 3 — SL đủ rộng** [S10][S13]:
- SL phải rộng để "giá thở"; ví dụ ~100 pip với EURUSD.
- SL bóp chặt sẽ bị quét dù hướng đi cuối cùng đúng.
- Trần cứng: không quá 100-120 pip từ entry (EURUSD); JPY ≥80 pip [S31].

**Sonic M — sizing** [S09][S42]:
- Rủi ro cố định theo phần trăm tài khoản, tính trên SL tối thiểu 50 pip.
- Quy ước thread: đếm pip, không khoe lot — mọi người dùng size khác nhau.

**Đăng chart = bài tập** [S18]:
- Bắt buộc template chuẩn, đánh dấu rõ EP/TP/SL, mỗi post một hình.
- Thread được duy trì như giáo trình — post#1 yêu cầu đọc trước khi hỏi.

**Tin tức** [S04][S17]:
- FFCal dùng để BIẾT lúc nào cá mập có thể giũ giá quanh tin.
- KHÔNG có luật cấm trade quanh tin trong doctrine gốc — TAH thậm chí đọc vị trí giá trước tin để đoán hướng.
- Điểm này mâu thuẫn trực tiếp với GOAL hard-avoid của repo mình.

**Cuối tuần / qua đêm** [S16][S17]:
- Tài liệu gốc không cấm giữ lệnh cuối tuần hay qua đêm — các ví dụ nắm lệnh nhiều ngày.
- GOAL của mình cấm weekend và hạn chế qua đêm — khác doctrine.

## 6. Bản gốc vs các biến thể (kể cả biến thể Việt Nam — cập nhật round 1C với video bài giảng)

**Gốc Kyaw/TAH** [S06][S10][S13]: Dragon EMA34 H/C/L + Trend EMA89 + sóng 3 chân tại S&R + WHQ 25-pip + PVA 150%/200% + phiên London + 3 quy tắc kỷ luật.

**Traders Reality (TradingView)** [S21][S22][S23]: port trung thực logic PVA + thêm market boxes, EMA 5/13/50/200/800, pivot, ADR, "vector candle zones".

**5 gia đình biến thể Việt** (xếp từ trung thực → nhiễm nhất; bằng chứng = transcript video trong notebook + bài viết):

1. **tamnhindautu.org / Đăng Quang** [S31][S32][S58][S59] — bản viết gần TAH nhất: cùng đếm sóng L-H-HL→HH / H-L-LH→LL, trigger = nến chân 3 phá Dragon, re-entry tại "rào cản thứ 3", M15 + trend H1/H4/D1, giữ PVSRA+WHQ làm lõi nâng cao (nguyên văn: "PVSRA là một phương pháp phân tích, không phải là một phương pháp giao dịch"). Thêm: EMA200/610 làm S&R di động tuỳ chọn, liên hệ Elliott cho 34/89, SL ≥80 pip JPY — **và một công thức "cầu vồng" ngoài-Sonic ngay trong bài** (VD9).
2. **Nhật Hoài Trader** [S52] — giáo viên gần cơ chế gốc nhất (xem VD10): pullback đầu tiên về dải → nến đóng thoát dải = vào; SL 2 kiểu (chặt ngoài cực nhịp hồi / rộng ngoài swing lớn); TP S&R gần + trail theo pivot. Khác TAH: thêm Pivot Points, không dạy PVSRA/WHQ trong video.
3. **Lucy / Học Đầu Tư Forex** [S53][S54] — scalp theo nến từ chối: trend H4/H1 → vào M15/M5/M1 (M5 "hiệu quả và an toàn nhất"); trigger = nến từ chối (pin/doji/engulfing) tại Dragon hoặc EMA89; SL dưới râu nến (chặt hơn TAH nhiều); TP chủ động trước khi hết sóng Elliott-5. Không PVSRA/WHQ.
4. **TRADERPTKT / Bài 14** [S55] — hệ EMA-bounce đội lốt Sonic: thêm EMA200 (tím)/EMA610 (bạc) làm S&R di động, so sánh dải EMA34 với mây Kumo, từ vựng SMC/BOS, cho phép đánh ngược trend tại kháng cự mạnh; **SL phía kia dải band (không phải swing), TP cố định 2R** — cả hai đều NGƯỢC giáo lý TAH.
5. **Hai kênh nhiễm — tách riêng**: [S56 Sell-thuận] chồng EMA200/610 đọc trend "rất mạnh" + **nhồi lệnh Sell khi giá chạm các đường MA** (transcript tự động bị lỗi chữ, ý nghĩa đã verify qua nhiều đoạn cite — đây là quote chuẩn hoá) — vi phạm trực tiếp quy tắc 2 của TAH; [S57 StochRSI/BB] thêm Stoch RSI + Bollinger Bands + EMA200/610 stack, SL tại đỉnh cũ + TP từng phần — không thấy nhồi lệnh. Cả hai: NHIỄM — không port.
- **Nguồn viết cũ**: topsanfx [S35] (EMA200/610 + Elliott + pullback-về-EMA), giaodichtaichinh [S36] (EMA200 + pin/engulfing + ADX/BB + cầu vồng), traderviet [S33] (thực hành gần gốc nhất, GBPJPY +140p).
- **Không dùng được**: 2 video zoom "nâng cao"/Elliott bị login-wall; video "Team hv Sonic R + Elliott + Fibo + Pitago" NLM không đọc được (fail ×2).
- **Anh đang theo dòng nào?** (giả thuyết): repo mình khớp dòng (1)-(2) — không có EMA200/610/RSI đâu. Nếu anh học qua video thì khả năng là (3) hoặc (4) — trigger/SL/TP của chúng khác hẳn nên em phải hỏi trước khi build (mục 10 câu 1).
- **Nhiễu khác cần loại**: ForexStrategiesResources "full version" (QQE/CCI63/50SMA/Stealth LCD) [S30]; sanforex.live domain rác [S44]; reseller indicator [S34].

## 7. Mình đã thử gì trước đây — ma trận fidelity (sửa lại số liệu round 1)

Bảng so sánh 10 lần thử với 11 yếu tố của Classic gốc (sóng L-H-HL; sóng tại S&R; chân-1-xuyên-Dragon; góc Dragon; đúng phía Trend; chân-3-đóng-thoát-Dragon; stop-order vài pip ngoài nến; SL ngoài swing lớn ≤120 pip; TP S&R lịch sử; phiên London; ≤5/tuần + không nhồi lỗ). `P`=có, `~`=xấp xỉ, `-`=thiếu, `X`=mâu thuẫn. Chi tiết: `SONICR_ATLAS.md` S8.

| Lần thử | Đối tượng | Kết quả (số thật) | Điểm yếu vs bản gốc | Số phận |
|---|---|---|---|---|
| S360 Dragon bounce/break (07/2026) | chạm/phá dải EMA34 + Trend | EU bounce PF 0.98, break 0.58, UJ 0.27, GU 0.45; XAU ~0 lệnh | chỉ có Trend+phiên; không sóng, không S&R, không runway | kill — EMA chạm không dự đoán nến sau [S45] |
| ITSM 5-13-34-89 (S506-S702) | pullback theo chồng EMA | S506-508 GBP/EU/XAU PF 0.62-0.99; con-cháu USDJPY = KILL_NO_REVIVAL; S701 EU 0.895, S702 XAU 0.84 | không neo S&R, không trigger Classic | kill — curve-fit theo cặp [S45] |
| Archive EA_SonicR XAU/AutoSleeve | EA ~50 input, router nhiều route (CLASSIC touch/DRAGON_PB/REVERSAL) | XAU 2024-25 **PF 1.41** (127 lệnh), 2021-25 **PF 1.16** (335), AutoSleeve=true; M5 seeds 2024-25 PF 1.32-1.78 nhưng 2019-25 PF **0.952** trên 492 lệnh; SIDEWAY_WIDE = túi lỗ chính (nhóm số M5 seeds = Lead-brief, không lưu local) | "CLASSIC" của nó là touch-logic không phải sóng 3 chân; nhiều route ngoài-source | **PARK vào kho 31/08 — KHÔNG bị kill**; chạy lại đúng-object bị chặn vì thiếu SNR_FX_EVENTS.csv [S45] |
| Grok SonicR v10 (08/2026) | EA H1 trên dữ liệu yfinance, đọc HTF fail-open | audit NOT_A_CANDIDATE_ENGINEERING_DONOR_ONLY; recovery thiếu fold assignment + OOS ledger | không phải object Sonic — là một EA khác | loại; chỉ làm donor plumbing [S45] |
| Scanner-Alignment (05/2026) | 262 scanner candidates của archive vs hướng đi 6 nến sau | **0/262 alignment; LONG_CONTEXT_FAIL chiếm đa số** (Lead cung cấp; ledger mất trong cleanup 31/08 — không verify được local) | nhãn scanner không chứa thông tin dự báo | — |
| EUR London Classic V1 | route Classic trực tiếp đầu tiên | 49,558 signal → **0 lệnh** (bug route-scope); sửa xong **2 lệnh/2 năm** (packet không lưu con số PF) | quá thưa | kill — cadence ~0 [S45] |
| EUR density batch | 3 màn hình: M5 T1 / M15 no-PVSRA / M15 source-core | M5 T1: PF 0.505 (4 lệnh theo Lead — packet chỉ ghi PF); M15 no-PVSRA: 2 lệnh; M15 source-core: 14 lệnh PF 1.28; nhãn trap_risk/late_chase lại NET DƯƠNG → không được làm veto | cadence/edge fail | kill [S45] |
| Hybrid ICT-Sonic | AND-stack H4 BOS/FVG/liq + sóng M15 + Dragon + climax + phiên | **N=0 nhiều năm**; diagnostic bỏ floor Dragon ±40 vẫn fail 1505/1508 SL-cap; terminal PF 0.98 @0.22 lệnh/tuần | floor SL ±40 mâu thuẫn SL-swing-rộng của gốc | kill — AND-stack bóp nghẹt tín hiệu [S45] |
| Draft 12/08 PVA-pullback | pullback gating bằng PVA (chưa chạy) | REJECT_PRE_SOURCE_DEDUP_FAIL | PVA làm cổng = sai giáo lý | loại trước đăng ký [S45] |
| **16/08 Classic geometry `20260816_205426`** | `ClassicWaveLeg3DragonBreak` Model-0 — object Classic cơ học trung thực nhất từng chạy | EURUSD M15 London: **N=307, PF 0.94** | đúng 6/11 yếu tố, 5/11 còn xấp xỉ (sóng-tại-S&R→khoảng-pip-tới-lưới-25; chân-1→chỉ là cờ; góc→slope-3-nến; SL→chân-1-extreme chứ không phải "swing lớn"; TP→lưới WHQ chứ không phải S&R lịch sử) | **KILL hẹp** — cấm thêm context-gate lên object này [S45] |

**Kết luận thẳng: chưa bao giờ test đúng bản gốc — và lần gần nhất cũng đã thua.** Run 16/08 code đúng W1/W5/W6/E1/S1/D1 nhưng PF 0.94 trên N=307 → hoặc (a) phần discretionary (chất sóng, PVSRA mode, cảm giác runway) mới là edge, hoặc (b) lõi cơ học vốn không có edge. Chỉ phân biệt được bằng cách test TỪNG mảnh thiếu trên scanner — tuyệt đối không chạy lại object 16/08 với thêm gate [S45][S46].

## 8. Mâu thuẫn với mục tiêu scalping 10-40 lệnh/tuần

- Doctrine: ≤5 lệnh/tuần **cấp tài khoản** (không phải mỗi symbol), M15 phiên London, SL ~100 pip, TP 50-400+ pip, giữ nhiều giờ tới nhiều ngày [S10][S13][S18].
- GOAL: 10-40 lệnh/tuần/symbol, scalping, cấm weekend, tránh tin, hạn chế qua đêm [S46].
- Chênh lệch: cadence doctrine thấp hơn GOAL **10-50 lần**; thời gian giữ lệnh dài hơn hẳn; tin tức là "quan sát" chứ không "cấm" [S04][S17].
- Các lựa chọn (để anh và Lead quyết): (1) nhiều symbol song song giữ đúng M15 London Classic — vẫn không đủ cadence/symbol nhưng giữ fidelity; (2) biến thể M5 — TAH cho phép cho scalping/entry sớm, cảnh báo mất xác nhận [S08]; (3) gộp Classic+Re-entry+Scout — Scout rủi ro/discretionary [S08]; (4) Sonic làm lớp ngữ cảnh cho trigger khác; (5) chế độ alert/assistant người-vào-lệnh; (6) đóng lane Sonic.

## 9. Hướng EA đề xuất (top 3) và bước tiếp theo

1. **S&R-ZONE (kiểu Volman) + parser sóng chuẩn cho Classic** — thay mức-cứng bằng vùng S&R từ engine perception sẵn có; parser zigzag/ATR trên nến đóng mã hoá đúng L-H-HL + chân-1-xuyên-Dragon + chân-3-đóng-cửa-thoát. Đây là 2 mảnh cơ học duy nhất chưa từng code đúng. Falsification: đếm event/tuần/symbol (mù-kết-quả), kill nếu <2-3 event/tuần EURUSD London [S10][S15].
2. **Nhãn regime PVSRA đo được (KHÔNG phải cổng)** — scalar "MM direction" = tỷ trọng volume climax/rising nằm dưới-vs-trên S&R gần nhất trong N nến; test xem regime score có tách được nhịp +50pip vs −50pip không. Falsification: KS test p>0.05 hoặc không có lift đơn điệu → kill [S12][S45].
3. **HTF context + LTF execution** — regime H1 (vị trí volume so với S&R) làm gate trạng thái, entry M5/M15 Dragon-break trong phiên London — đúng cách TAH ghép H1→M15 và M5 được phép cho scalping [S15][S08]. Falsification: độ đồng thuận proxy H1 vs kết quả Classic M15 <55% thì kill.

Bước tiếp theo đề nghị: chạy falsification (1)+(2) ở chế độ **scanner/label** trước — chưa build EA.

## 9b. Round 1B đã sửa/học được gì mới

- File PVA canonical `Sonic_2_PVA_Candles_White_20140317.mq4` đã về qua Drive và hash-khớp → phán quyết PVA chốt trên chính file gốc 2014, không còn phải suy từ Suite 2015 [S51].
- Định nghĩa climax của TAH thừa nhận lấy từ BetterVolume_v1.4 — gốc rễ VSA, giải thích vì sao Traders Reality dùng y hệt ngưỡng [S51].
- Trang 3756 của thread (TAH, 16/08/2014) được lưu full text `primary/ff_page3756_*.txt`: Scout được định nghĩa đầy đủ 2 dạng trong post 7679382; còn quote M5/London nằm trong post TAH **ngay trên** 7679382 cùng trang — "you can try the M5 TF... Classic entries are only recommend during the London session" [S08].
- Phát hiện NotebookLM có thể trả lời SAI: nó nói "không có nguồn nào cho phép M5" — đọc trực tiếp post gốc cho thấy ngược lại. Bài học: chỉ tin passage đã tự đọc.
- Archive EA_SonicR: đính chính — bị PARK vào kho 31/08 chứ không phải "bị kill"; số PF 1.41/127 và 1.16/335 là thật từ catalog; tái-chạy bị chặn bởi file SNR_FX_EVENTS.csv mất [S45].
- EUR London Classic V1: đính chính — không phải "edge âm" mà là 0 lệnh (bug) → 2 lệnh/2 năm (packet không lưu PF), chết vì quá thưa [S45].
- EUR density batch: đính chính — là 3 màn hình riêng (M5 T1 PF 0.505 — 4 lệnh theo Lead; M15 no-PVSRA 2 lệnh; M15 source-core 14 lệnh PF 1.28); nhãn trap_risk/late_chase NET DƯƠNG nên không được dùng làm veto [S45].
- Grok v10 tách khỏi archive thành 2 object khác nhau: v10 = EA H1 yfinance fail-open (donor-only), archive = EA XAU AutoSleeve (parked) [S45].
- Lưới XAU suy ra từ code: `Poin = Point*10` → trên vàng 2-digit cùng code TAH vẽ quarter $2.50/half $5/whole $10 — không còn là con số đoán [S03 dòng 713].
- NotebookLM pass 2: +1 nguồn (file PVA 2014), 6 gap-query có citation; YouTube Việt không tồn tại qua tìm kiếm — **đính chính round 1C**: Lead tìm được, video VN thật sự có (mục 9c); 3 video Tây Ban Nha đã chết; video "của Sonic" resolve sang video súng (đã xoá khỏi notebook).
- ≤5 lệnh/tuần: xác nhận là quy tắc cấp tài khoản, không phải mỗi cặp — verbatim post#1 bảo tồn qua NLM cited_text của mirror S10 (file S18 không còn rules list).
- "Several pips": nguồn không cho số — đó là buffer tuỳ ý; số 3 pip trong spec mình là reconstructed [S10][S11].

### 9c. Round 1C thêm gì (Vietnamese pass)

- 6 video bài giảng Việt vào notebook (đã kiểm captions trước khi add): Nhật Hoài, Lucy ×2, Bài 14 chuyên sâu, Sell-thuận, video StochRSI/BB; +2 trang tamnhindautu (1 trang resolve trùng bài S32).
- Kết quả: cộng đồng Việt chia thành 5 dòng rõ rệt (mục 6) — chỉ tamnhindautu + Nhật Hoài giữ cơ chế gốc; Lucy đổi trigger thành nến từ chối; Bài 14 là hệ EMA-bounce (SL qua band, TP 2R); hai kênh kia nhồi lệnh/indicator-lạ = nhiễm.
- Hầu hết giáo viên Việt trên YouTube BỎ PVSRA và lưới WHQ — chỉ bản viết tamnhindautu giữ chúng làm lõi nâng cao.
- Bỏ qua: 2 video login-wall, 1 video Elliott NLM không đọc được, 2 trang web timeout, Scribd (read-only theo Lead).

## 10. Câu hỏi cho anh (tối đa 5)

1. Anh học Sonic R từ nguồn nào — chọn một dòng trong menu round 1C: (a) thread FF gốc / tamnhindautu (chuẩn TAH); (b) video Nhật Hoài scalping M15 (chuẩn cơ chế + pivot, không PVSRA); (c) Lucy rejection-scalp H4→M5/M1 (nến từ chối, SL dưới râu nến); (d) TRADERPTKT/Bài-14 EMA-bounce + EMA200/610, SL qua band, TP 2R; (e) kênh Chỉ-Báo-SONIC-R StochRSI/BB (nhiễm). Repo mình khớp (a)/(b); nếu anh theo (c)/(d) trigger/SL/TP khác hẳn — cần biết trước khi build.
2. Symbol/khung anh muốn: chỉ XAUUSD M15, hay cả majors FX, và có chấp nhận entry M5 scalping (TAH cho phép, mất xác nhận)?
3. Cadence: chấp nhận ~2-5 lệnh/tuần/symbol đúng-chuẩn (post#1 cap = cấp tài khoản, Kyaw chủ yếu 1 cặp), hay bắt buộc 10-40 (→ biến thể)?
4. News: giữ hard-avoid của GOAL hay theo doctrine gốc (quan sát, không cấm)?
5. Nếu lõi cơ học Classic thật sự không có edge: anh muốn Sonic-as-scanner cảnh báo cho người, hay đóng hẳn lane?

## 11. Từ điển nhanh (glossary)

| Thuật ngữ | Nghĩa |
|---|---|
| Dragon | Dải 3 EMA34 (High/Close/Low) tô đầy — công cụ chọn điểm vào lệnh [S49] |
| Trend | Đường EMA89 Close — xác nhận hướng giao dịch [S49] |
| Wave (sóng) | Cấu trúc giá 3 chân: L-H-HL (mua, bắt đầu dưới Dragon) hoặc H-L-LH (bán, trên Dragon) [S10] |
| Leg 1/2/3 | Ba chân sóng; chân 1 nên xuyên qua Dragon, chân 3 phải đóng cửa thoát ra [S10] |
| WHQ | Lưới Whole/Half/Quarter — mức giá 00/50/25/75 trong mỗi 100 pip; quan trọng giảm dần [S03][S12] |
| Runway | "Đường băng" — khoảng trống không có S&R mạnh ngay phía trước entry [S15] |
| PVA | Price-Volume Analysis — luật tô màu nến theo volume (rising ≥1.5×, climax ≥2×/spread×vol max của 10 nến trước) [S51] |
| PVSRA | Phân tích Giá+Volume+S&R — đọc xem MM là phe mua/bán và đang "gom" hay "chạy lời" [S12] |
| Climax | Nến volume cực lớn (≥2× trung bình 10 nến trước, hoặc spread×vol lớn nhất 10 nến) — màu xanh lá/đỏ [S51] |
| Rising | Nến volume cao (≥1.5×) chưa tới climax — màu xanh dương/tím [S51] |
| Position building | Pha MM đang gom/xả — giá đi NGƯỢC hướng vị thế của họ; đừng vào [S12] |
| Run for profits | Pha MM đang đẩy giá theo hướng lời của họ — chỉ trade theo hướng này [S12] |
| Classic | Setup lõi: sóng tại S&R + chân 3 phá Dragon + stop-order vài pip ngoài nến [S10] |
| Scout | Entry sớm trước/trong Classic — trước Classic = ngược trend rủi ro cao; trong Classic ≈ re-entry [S08] |
| Re-entry | Thêm lệnh vào Classic đang xanh trong nhịp hồi [S08][S10] |
| Sonic M | Cách sizing của Kyaw: rủi ro cố định trên SL ≥50 pip [S09] |
| Stop Hunt | Pha MM quét thanh khoản — lý do không nhồi lệnh khi Classic đang đỏ [S08] |
| RDH/RDL/RWH/RWL | Range trung bình ngày/tuần trên Access Panel — mốc tham chiếu TP [S03] |

---

*Phụ lục nguồn chính đã đọc trực tiếp: code TAH — `primary/Candles-Suite.mq4`, `Volumes-Suite.mq4`, `Access-Panel.mq4`, `FFCal-Panel.mq4`, `SonicR_PV_Histogram_Black_2011.mq4`, `drive/SonicR_Filled_Dragon_White.mq4` (hash khớp manifest), `drive/Sonic_2_PVA_Candles_White_20140317.mq4` (hash khớp zip canonical — file PVA 2014 chính chủ); bài TAH/Kyaw qua wayback — post#1 (2014+2020), 7348659, trang 3756 = post 7679382 + post TAH ngay trên (full text lưu tại `primary/ff_page3756_*.txt`), 6488843; mirror — sonicr999, th3-pro, forexonsignal, sgtradingcourses; Việt Nam — tamnhindautu×2, traderviet, topsanfx/giaodichtaichinh (đã flag mức nhiễm). NotebookLM "Sonic R System" (id 8490421d): 31 nguồn (gồm 6 video bài giảng Việt: Nhật Hoài, Lucy ×2, Bài 14, Sell-thuận, StochRSI/BB), 17 câu hỏi, report + data table + audio tiếng Việt đã render — anh mở xem trực tiếp. Còn thiếu: file quarantine gốc tháng 5 (chỉ khôi phục được 2 file qua Drive), ảnh chart đính kèm (CDN chặn TLS), Trade Levels bản Mar-2014, mind map (lỗi INVALID_ARGUMENT của NotebookLM).*
