# GOAL — Mục Tiêu Tự Do

Cập nhật mục tiêu: 2026-07-31 theo clarification của Owner về chuỗi T1→T100,
cadence theo từng symbol và ưu tiên scalping M5/M15.

File này chỉ định nghĩa mục tiêu cấp workspace và điều kiện DONE. Trạng thái
hypothesis/run lấy từ registry, prereg, task packet và artifact đã xác minh;
`04. Memory/hot.md` chỉ là cache handoff gần nhất. Lịch sử campaign nằm trong
package research, `STRATEGY_LOG.md`, failure catalog và archive — không nằm ở
GOAL.

Một lane `parked|killed`, delivery packet `KILLED`, compile xanh hoặc search
cell `NO LEGAL CANDIDATE` không hoàn thành mục tiêu. Mục tiêu vẫn `ACTIVE / UNMET`
cho tới khi ít nhất một symbol-sleeve đạt target tối thiểu bên dưới; chỉ Owner
mới đổi, mở rộng hoặc dừng mục tiêu.

## Mục tiêu kinh tế

Tạo ít nhất một symbol-sleeve scalping M5/M15 có edge thực, được xác minh bằng
MT5/AlphaFactory trên toàn bộ lịch sử MT5 khả dụng của từng symbol; cửa sổ
2018-current vẫn phải được báo cáo riêng khi symbol có đủ coverage. Mỗi
symbol-sleeve được claim phải đạt **đồng thời**:

| Chiều | Mục tiêu |
|---|---|
| Profit factor | > 1.30 sau cost thật đã xác minh (x1) |
| Cadence | 2–5 executed trade/elapsed calendar week trên chính symbol đó, ở từng split train/validation/OOS/holdout liên quan; không pooled symbol, không active-week |
| Timeframe | Entry/economic timeframe ưu tiên M5 hoặc M15; H1/H4/D1 chỉ làm context/regime nếu prereg |
| Required backtest universe | XAUUSD, BTCUSD và 7 FX majors thanh khoản cao: EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD, NZDUSD; không được bỏ cell chỉ vì thiếu Model-4/cost promotion evidence |
| History quality | Strategy Tester history quality phải >97%; coverage %, clock, gaps, bid/ask và cost vẫn được audit riêng theo claim |
| Cost stress | x1.5 PF >= 1.25; x2 PF >= 1.00 |
| Exposure | Hạn chế giữ qua đêm và không giữ qua cuối tuần theo scalp contract |
| Drawdown | Monte Carlo P95 DD nằm trong risk budget đã khai báo |
| Cửa sổ evidence | 84 tháng / 14 nửa năm / 7 năm cho cấp confirmed |
| Split | Train và holdout phải tự pass độc lập |

Ngưỡng chi tiết, artifact theo stage và hard invalidation có thẩm quyền nằm ở
`05. Playbook/validation_gates.md`. Nếu bảng tóm tắt trên mâu thuẫn với gates,
file gates thắng.

## Target tối thiểu và DONE nghĩa là gì

1. `research pass` — matched Model 0 control/challenger, cost stress thận trọng
   và đủ cadence; chỉ cấp quyền đầu tư thêm effort.
2. `confirmed symbol-sleeve / T-loop target` — ít nhất một symbol tự đạt PF,
   cadence 2–5/tuần trên từng split và toàn bộ gate promotion: train/holdout
   độc lập cùng pass, optimization-aware WFA,
   PBO/Reality Check theo prereg, Monte Carlo, execution/equity audit, cost
   provenance cùng broker, Heavy-Delivery/forensics và artifact
   promotion-eligible. Khi đạt mức này, dừng sinh T(n+1) và tập trung đóng gói
   survivor; không đồng nghĩa tự động live.
3. `portfolio expansion / pro-trader book` — sau target tối thiểu, có thể mở
   rộng thêm symbol/sleeve confirmed đủ độc lập, pass correlation/overlap và
   cost stress gộp. Mỗi symbol thêm vào vẫn phải tự pass; symbol thua không được
   cứu bằng số gộp.
4. `deploy` — quyết định riêng của Owner sau khi hoàn tất 1–3; nghiên cứu không
   tự cấp quyền paper/live.

## Không được tính là DONE

- PF cao nhưng chính symbol được claim nằm ngoài 2–5 trade/elapsed week trên
  bất kỳ split nào.
- Gộp trade/PF của nhiều symbol để che một symbol không đạt cadence hoặc edge.
- Backtest đẹp nhưng cost provenance chưa xác minh.
- Compile/test/pass kỹ thuật nhưng chưa pass kinh tế.
- Filter hoặc tham số được đào từ chính readout vừa tạo.
- Một terminal verdict, một source frontier hoặc một prompt research hết ứng viên.
- Hoàn hảo quy trình nhưng chưa tạo tiến triển về expectancy.

## Nguyên tắc tiến tới mục tiêu

- T1, T2, ... T100 là các strategy generation **tuần tự**, không phải phòng ban
  hay tầng evidence. Một thời điểm chỉ một Tn có quyền build/run. Tn chỉ nhường
  quyền cho T(n+1) sau verdict hợp lệ và failure/capability packet.
- T1 = Hurst/VWAP/quant graph; T2 = Bob Volman price-action grammar; T3 = SMC
  causal/liquidity model; T4–T100 chọn từ capability gap của thế hệ trước.
- Mỗi Tn có economic authority phải backtest toàn bộ required universe bằng
  history MT5 khả dụng. Model 0 có thể cung cấp economics nếu >97%; Model 4 chỉ
  bắt buộc cho claim phụ thuộc thứ tự real-tick/intrabar. Thiếu Model 4 không
  cho phép bỏ symbol, nhưng phải hạ cấp claim fidelity tương ứng.
- Discovery và probe offline rẻ trước; ceremony nặng chỉ dành cho candidate còn
  sống.
- Mỗi meaningful run phải có hypothesis ID, registry row, prereg và contract
  đóng băng trước outcome.
- Một kill chỉ đóng đúng tested object. Sau failure hợp lệ: ghi failure radius,
  rồi chọn repair run vô hiệu, mở cơ chế/ID mới, hoặc nêu blocker thật cần Owner.
- Optimization tìm vùng ổn định, không săn đỉnh; position sizing không được dùng
  để che signal âm.
- Ưu tiên expectancy sau phí, stability theo thời gian/regime, tail risk và khả
  năng khớp lệnh hơn PF in-sample đứng riêng.
- Nếu T100 vẫn chưa đạt, goal vẫn `UNMET`: meta-review độc lập, giữ nguyên trial
  debt/holdout exposure rồi quay Phase 0 của campaign epoch kế tiếp; không tuyên
  bố thị trường hết edge hoặc năng lực hiện tại là frontier của pro trader.
