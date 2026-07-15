# GOAL — Mục Tiêu Tự Do

Cập nhật: 2026-07-11

File này chỉ nêu mục tiêu. Chỉ thay đổi khi Owner quyết định rõ ràng.
Tiến độ sống, blocker, và lane đang hoạt động nằm ở
`04. Memory/hot.md` — không bao giờ nằm ở đây.

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
`05. Playbook/sonic_validation_gates.md`. Nếu bảng này và file đó
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
