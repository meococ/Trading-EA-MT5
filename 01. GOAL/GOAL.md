# GOAL — Mục Tiêu Tự Do

Cập nhật: 2026-07-16

File này chỉ nêu mục tiêu. Chỉ thay đổi khi Owner quyết định rõ ràng.
Tiến độ sống, blocker, và lane đang hoạt động nằm ở
`04. Memory/hot.md` — không bao giờ nằm ở đây.

## Mục tiêu active — phát triển EA sau campaign Unicorn (Owner duyệt 2026-07-16)

Hoàn thiện `EA_UnicornPrecisionScalper` bằng một vòng nghiên cứu có giới hạn,
backtest Model 0 thật và verdict không thiên lệch. Campaign này đã đi đến điểm
kết thúc bằng evidence, không phải bằng một EA được phép giao dịch:

1. Control bốn-bar `HYP-UPSC-XAU-M5-002` đã KILL: PF sau research cost `0.688`,
   cadence `1.334/tuần`, robustness `0%`.
2. Cơ chế event-anchored được đóng băng trước outcome, qua probe/build dưới
   HYP-005 rồi chạy hợp lệ qua operational successor `HYP-UPS-XAU-M5-006`.
3. HYP-006 đã KILL: PF tester `0.724`, PF sau research cost `0.498`, cadence
   `1.257/tuần`, Monte Carlo P95 DD `7.118%`, equity `REJECT`; kém control trên
   các thước đo trung tâm. Không được cứu bằng lọc giờ/ngày, sweep-age, RR,
   session hoặc score.
4. Source/readout/run hợp lệ giữ trên `D:`. Inventory C trước/sau giống tuyệt
   đối; không có file run-owned trên C để xóa và không đụng dữ liệu dùng chung.
5. Mục tiêu tiếp theo chỉ cho phép một cơ chế nhân quả mới, khác family
   fixed-expiry/event-expiry, đi lại de-dup → probe không outcome → prereg →
   code/non-repaint/compile → Model 0. Không live/paper attach và không hứa lợi
   nhuận.
6. Theo chỉ đạo Owner, canonical source đã được harden hậu kiểm thành kernel
   alert-only fail-closed: FSM execution, ownership đầy đủ, broker/order preflight,
   cost-aware sizing, restart/partial-fill/risk-state safety và reject telemetry.
   Gate kỹ thuật đạt 30/30 test, compile 0/0 và exact-source non-repaint PASS;
   hardening này không cấp lại performance authority cho family đã KILL.
7. Theo yêu cầu research tiếp của Owner, Grok 4.5 và kiểm tra nguồn sơ cấp kết
   luận chưa có candidate giao dịch mới hợp lệ trên data hiện có. Canonical EA
   được nâng lên v1.20 bằng `ALERT_FIRST_CASEBOOK_V1`: opt-in, alert-only,
   D-drive-only, tối đa 200 dòng, không outcome và không đổi signal. Gate kỹ
   thuật hiện tại 34/34 test, compile 0/0 và exact-source non-repaint PASS. Chỉ
   được mở hypothesis kinh tế mới sau khi có tối thiểu 100 nhãn pre-outcome và
   analysis plan riêng đã đóng băng.

Campaign Unicorn đã hoàn tất về mặt nghiên cứu với verdict KILL; “Mục Tiêu Tự
Do” của toàn workspace vẫn UNMET. Việc tiếp tục phát triển không đồng nghĩa
tiếp tục tinh chỉnh family đã bị falsify.

## Mục tiêu lane KLR-Scalper được Owner mở ngày 2026-07-16

Đánh giá để chỉ xây dựng `EA_KLR_Scalper` tại `03. EA Developer/` từ
`KLR_Scalper_Deep_Research_Report` khi family vượt de-dup và probe đóng băng;
sau đó mới được code → audit non-repaint → compile → matched Model 0 → phân
tích. Evidence PO3-AMD cùng cơ chế được tính là cùng một family, không được coi
là run độc lập hay đổi tên để rescue.

- Primary `XAUUSD`, M15 context và M5 execution; closed-bar only.
- Không tự bịa ngưỡng còn thiếu trong report sau khi đã đọc kết quả.
- Không tạo `.mq5`, compile hoặc Strategy Tester nếu probe family đã kill.
- Không live, không attach tài khoản thật, không hứa lợi nhuận.
- Mọi terminal/tester data của lane mới phải nằm vật lý trên `D:`; binary MT5
  có thể ở `C:` nhưng không được dùng data/tester root trên `C:`.

## Mục tiêu lane Unicorn được Owner mở ngày 2026-07-16

Xây dựng `EA_UnicornPrecisionScalper` tại `03. EA Developer/` từ report
Unicorn, theo generic golden path và không bịa cost để ép Strategy Tester chạy.

- Primary `XAUUSD`, execution `M5`, bias H4/D1, default alert-only; research
  auto phải được bật rõ trong task packet.
- Hypothesis 001 exact-adjacency đã park ở probe; hypothesis 002 stateful-sweep
  đã pass probe, compile và non-repaint, hiện `screened`.
- Model 0 chỉ được chạy khi có verified same-broker spread/commission/slippage
  manifest. Thiếu cost là blocker, không phải cost bằng 0.
- Không live/paper attach, không post-hoc rescue, không hứa lợi nhuận.
- Sau tester run hợp lệ: giữ/hash evidence trên `D:` trước, rồi xóa cache/train/
  log tester có thể tái tạo trên `C:` mà không đụng account/profile/history dùng
  chung.

## Mục tiêu lane PO3-AMD được Owner mở ngày 2026-07-16

Xây dựng `EA_PO3_AMD_Scalper` tại `03. EA Developer/` từ report PO3-AMD,
theo generic golden path: de-dup → probe offline → prereg đóng băng → code →
audit non-repaint → compile → matched Model 0 → phân tích/kill hoặc tiếp tục.

- Phase đầu chỉ dùng `XAUUSD`, execution `M5`, một symbol/một instance.
- Train khóa `2022-2024`; `2025` là holdout chưa được mở khi thiết kế;
  `2026 YTD` chỉ là shadow sau này.
- Không được rescue hậu nghiệm nếu probe hoặc Model 0 fail.
- Không live, không attach EA vào tài khoản thật, không tuyên bố deploy-ready.
- Sau mỗi backtest, giữ evidence đã hash ở `02. AlphaFactory/runs/` trên `D:`
  và dọn cache/train/log tester có thể tái tạo trên `C:` sau khi terminal dừng.
- Lane này vẫn phục vụ mục tiêu book bên dưới; một research pass riêng lẻ chưa
  hoàn thành Mục Tiêu Tự Do.

## Mục tiêu

Một book FX (một hoặc nhiều EA sleeve) đạt TẤT CẢ các điều kiện sau cùng
lúc, với evidence cấp promotion:

| Chiều | Mục tiêu |
|---|---|
| Profit factor | > 1.30 sau cost thật đã xác minh (x1) |
| Cadence | 2–5 trade/tuần mỗi split, tính theo tuần lịch trôi qua (elapsed calendar weeks) |
| Cost stress | x1.5 PF >= 1.25; x2 PF >= 1.00 |
| Exposure | Hạn chế giữ lệnh qua đêm/ và không để lệnh qua cuối tuần theo scalp contract |
| Drawdown | Monte Carlo P95 DD nằm trong risk budget đã khai báo |
| Cửa sổ evidence | 84 tháng / 14 nửa năm / 7 năm cho cấp confirmed |
| Split | train và holdout mỗi cái tự pass độc lập |

Ngưỡng số, artifact theo stage, và hard invalidation có thẩm quyền nằm ở:
`05. Playbook/validation_gates.md`. Nếu bảng này và file đó
mâu thuẫn, file gates thắng.

## DONE nghĩa là gì (thang evidence)

1. `research pass` — matched Model 0 control/challenger cộng cost stress
   thận trọng. Không cấp quyền gì ngoài quyền được tiêu thêm effort.
2. `confirmed` — bộ promotion đầy đủ (optimization-aware WFA, PBO/Reality
   Check aligned theo prereg, Monte Carlo, audit execution/equity) với
   artifact promotion-eligible và cost provenance cùng-broker.
3. `portfolio-sleeve` — ít nhất hai sleeve confirmed độc lập, pass
   correlation/overlap và cost stress gộp.
4. Triển khai — quyết định riêng của Owner, sau khi có 1–3.

## Non-goals (nói rõ để khỏi tự lừa)

- PF cao ở dưới 2 trade/tuần (sleeve thưa không phải là book).
- Backtest đẹp mà không có cost provenance từ broker.
- Rescue filter đào từ chính readout vừa tạo ra.
- Hoàn hảo quy trình vì chính nó — ceremony validation dành riêng cho
  survivor của probe.

## Nguyên tắc vận hành

Discovery trước ceremony: mọi hypothesis phải qua một probe offline rẻ trên
artifacts sẵn có trước khi được tiêu effort prereg -> code -> Model 0.
Đo bằng số hypothesis chất lượng được screen mỗi tuần; kill nhanh là một
kết quả tốt.
