# HOW TO USE — VPA_Vision

`VPA_Vision.mq5` là indicator MT5 **visual-only**, không có code giao dịch. Nó vẽ đúng những gì detector Python DR3 (đã freeze) "thấy" trên chart M5: touch-cluster barrier, EMA25, ATR, và một annotation cho mỗi lần detector đánh giá candidate DR3 (ACCEPT/SKIP + gate fail + features). Thiết kế cho **EURUSD M5**.

## Gắn lên chart

1. Copy `VPA_Vision.ex5` vào `<MT5 data folder>\MQL5\Indicators\`.
   - Owner GUI: `%APPDATA%\MetaQuotes\Terminal\9CA16B8382AE4CF692710FB36B9DA355\MQL5\Indicators\`
   - Muốn dùng script parity: copy `VPA_Vision_Parity.ex5` vào `...\MQL5\Scripts\`.
2. Refresh Navigator (chuột phải → Refresh).
3. Kéo indicator vào chart **EURUSD M5**.
4. Chart không phải M5: indicator từ chối load, không vẽ gì (trừ khi bật `InpAllowNonM5`).

## Inputs

### Layers

| Input | Default | Ý nghĩa |
|---|---|---|
| `InpShowBarriers` | true | Vẽ barrier lines |
| `InpShowTouchMarkers` | true | Vẽ dấu touch |
| `InpShowEma` | true | Vẽ EMA25 |
| `InpShowAtrPanel` | true | Vẽ ATR panel |
| `InpShowEvents` | true | Vẽ annotation event (label, highlight, entry/stop/target) |
| `InpShowObstacle` | true | Vẽ đường obstacle |
| `InpShowAccepted` | true | Hiện event ACCEPT |
| `InpShowRejected` | true | Hiện event SKIP |

### Depth / scale

| Input | Default | Ý nghĩa |
|---|---|---|
| `InpHistoryBars` | 20000 | Số nến M5 nạp để dò barrier/event |
| `InpDrawBars` | 2000 | Chỉ vẽ N nến mới nhất (0 = vẽ hết depth) |
| `InpMaxEvents` | 300 | Trần số event được vẽ (tính từ event mới nhất) |
| `InpLabelFontSize` | 8 | Cỡ chữ label |
| `InpLabelOffsetPoints` | 40 | Offset label theo points |
| `InpAtrPanelBars` | 60 | Số giá trị trong spark của ATR panel |
| `InpAllowNonM5` | false | Bỏ chặn timeframe. Không nên bật: toàn bộ params DR3 là M5-frozen |

### Colors

| Input | Default |
|---|---|
| `InpColorBarrierUp` | `clrDeepSkyBlue` |
| `InpColorBarrierDn` | `clrOrangeRed` |
| `InpColorBarrierBad` | `clrDimGray` |
| `InpColorTouch` | `clrSilver` |
| `InpColorEma` | `clrGoldenrod` |
| `InpColorAccept` | `clrLimeGreen` |
| `InpColorSkip` | `clrTomato` |
| `InpColorEntry` | `clrRoyalBlue` |
| `InpColorStop` | `clrCrimson` |
| `InpColorTarget` | `clrMediumSeaGreen` |
| `InpColorObstacle` | `clrDarkOrange` |
| `InpColorLabel` | `clrWhiteSmoke` |
| `InpColorAtrPanel` | `clrSlateGray` |

## Ý nghĩa trên chart

**Barrier** — đường ngang tại mức touch-cluster B (median của các giá touch). Xanh = barrier pivot-high (trần, phía short), đỏ = barrier pivot-low (sàn, phía long). Sống 20 nến kể từ lock bar (expiry), biến mất sớm hơn nếu bị consumed.

**Touch markers** — mỗi nến có high (trần) / low (sàn) nhập cluster được đánh một dấu nhỏ, cách nhau >= 2 nến.

**Barrier DASHED GREY + chữ `integrity`** — integrity gate của DR3 fail cho barrier đó: giữa first touch và signal bar có một close vượt B quá 0.10*ATR. "Level bị closes cắt qua thì không phải barrier" — không phải bug.

**Signal bar highlight (rectangle)** — signal bar của DR3 (`signal_prev_bar=True`). Lưu ý: trong code frozen, danh sách `touches` của barrier xếp giảm dần nên `tch[-1]` luôn là **bar lock của barrier** (nến pivot đã lock nó). Vì vậy highlight thường nằm **3–10 nến về bên trái** chỗ detector đánh giá (bar breakout), không phải nến sát bên trái. Đây là hành vi thật của Python, indicator chỉ mirror lại.

**Entry / Stop / Target** — entry xanh dương, stop đỏ (entry -/+ 8 pips = `S`), target xanh lá (entry +/- 16 pips = 2R). Kéo dài qua signal bar + cửa sổ hiệu lực 3 nến. Chỉ có khi detector tìm ra buildup; không buildup = không có entry.

**Obstacle line (cam, ngắn)** — vật cản sinh ra `room_r`: obstacle gần nhất phía trước entry (pivot ±5 nến significant, barrier đang active, PDH/PDL, hoặc lưới round 00/50).

**Label 3 dòng**, right-anchored nên không đè cột giá:

1. `ACCEPT long` hoặc `SKIP long [trend,integrity]` — các HARD gate fail: warmup, session, direction, trend, integrity; cost luôn pass.
2. `B=... entry=... stop=... tgt=...` (hoặc `B=... no buildup`).
3. `room 2.41R ob=pivot_sig@1.12500 | ema 0.83A | sq Y | lunch N | chop Y(win N) | S=eu | A=...`
   - `room ...R` tính theo R (8 pips = 1R); `ob` = loại obstacle + giá.
   - `ema`/`sq`/`lunch`/`chop` là feature của DR3; `chop` hiện cả legacy 4-bar chop và giá trị trong cửa sổ buildup.
   - `S=` là session tại trigger bar: `eu` = 05:00–11:00 UTC, `us` = 11:30–17:30 UTC; `off` = ngoài session.
   - `A=` là ATR(14) tại signal bar.

**EMA25** — đường vàng, đúng recursion detector dùng (seed = mean 25 close đầu, alpha = 2/26). Không tính cho nến đang hình thành.

**ATR panel (góc trái-dưới)** — ATR(14) Wilder đúng như detector dùng: số + spark của `InpAtrPanelBars` giá trị gần nhất. Cũng in theo label qua `ema_dist_atr`/`A`.

**Chỉ dùng nến CLOSED** — nến đang chạy không bao giờ được evaluate nên không repaint. Mỗi evaluation chỉ vẽ một lần khi bar đóng; có nến mới thì redraw toàn bộ depth đang thấy. (Cuối tuần thị trường đóng, nến cuối vẫn bị giữ lại — chậm 1 nến so với "nến vừa đóng" của MT5, đổi lại không bao giờ repaint.)

**Objects prefix `VPA_VIS_`** — xóa sạch mỗi lần redraw và khi tắt indicator.

## Parity export (tùy chọn — cho Lead)

- `InpExportCsv` (default false). Bật lên, khi attach sẽ ghi `VPA_Vision_bars.csv`, `VPA_Vision_events.csv`, `VPA_Vision_barriers.csv` cho `InpExportFrom`..`InpExportTo` (default `2019.02.01`..`2019.04.01`, giờ server) vào `<MT5 data folder>\MQL5\Files\<InpExportFolder>\` (default `vis1`).
- Cách khuyến nghị: chạy script `VPA_Vision_Parity` (trong `MQL5\Scripts\`) — làm điều tương tự mà không đụng chart.
- Comparator bằng Python: `PLAN/vis1/compare_parity.py`, hướng dẫn đầy đủ trong `PLAN/vis1/PARITY.md`.

## Nếu lạ

- Không có gì hiện: kiểm tra chart đúng **M5** chưa; indicator không load trên TF khác.
- Thiếu dữ liệu: tăng `InpHistoryBars`, hoặc cuộn chart về vùng có history.
- Chart bị kéo lệch/thu nhỏ: bật AutoScroll, bấm "Scale" hoặc double-click trục giá.
- Objects biến mất: template đang áp có thể che/xóa chúng — apply lại template rồi gắn lại indicator.
- Event cũ bị cắt: đã đạt `InpMaxEvents` (hoặc `InpDrawBars`), tăng lên hoặc zoom vào vùng mới.
- Vẫn không thấy: kiểm tra các input Layers có đang bật không (đặc biệt `InpShowEvents`, `InpShowAccepted`, `InpShowRejected`).
