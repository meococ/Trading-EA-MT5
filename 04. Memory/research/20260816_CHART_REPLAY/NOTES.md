# 20260816 chart replay — ghi chú trader

Nguồn: deal `report.html` + OHLC portable `mt5-portable-mqdemo` (login 5054517252, MetaQuotes-Demo). Không Visual Tester, không đụng Program Files / FivePercent Real, không holdout. SL/TP trên chart là ảo dựng lại từ contract (broker SL/TP = 0). PF là observed, không phải edge.

Mẫu case đóng băng: 3 win lớn / 3 loss lớn / 2 median win / 2 median loss / cụm DD. Không cherry-pick.

OHLC M15 portable chỉ có từ **2022-05-17**. H1/H4 XAUUSD và H1 EURUSD đủ 2018–2023.

## Path

- Index: `04. Memory/research/20260816_CHART_REPLAY/index.html`
- Tổng 4 run ưu tiên: `00_OVERVIEW.html`
- SweepFade: `SWEEPFADE_20260816_130548.html` + `_overview.html` + `_cases.html`
- GBB S2: `GBB_S2_20260816_124307.html` + `_overview.html` + `_cases.html`
- Asia-London: `ASIA_LONDON_20260816_134530.html` + `_overview.html` + `_cases.html`
- Donchian H4: `H4_DONCHIAN_20260816_141128.html` + `_overview.html` + `_cases.html`
- PDBREAK EURUSD (nếu còn sức): `PDBREAK_20260816_140021.html` + `_overview.html` + `_cases.html`
- M15 TrendPB (nếu còn sức): `M15_TRENDPB_20260816_132913.html` — case vẽ **H1 context** vì 721 lệnh nằm 2018-01..2019-02, M15 portable không phủ
- Bảng case: `selected_cases.json`

## Bullet trader (Main cần nhìn)

1. **SweepFade vào đúng thesis, vẫn gần hòa.** 1150/1150 nến tín hiệu là wick xuyên PDH/PDL rồi close reclaim; entry open H1 kế. Chart không phải “EA vào lung tung”. PF 1.01 đến từ payoff: ~536 SL vs ~306 TP, cộng 198 daily-flat 21:50 và 58 Friday-flat cắt cả win lẫn loss. Europe +227, NY −115, Asia ~0. Case thua lớn 2022-02-21 sell fade PDH rồi vàng chạy tiếp — fade đúng cấu trúc, sai regime trend.

2. **GBB S2 không phải “sai nến”, mà clock ăn thịt R.** 582 lệnh, PF 0.81, net −787. Exit: 220 daily-flat + 50 Friday-flat; SL/TP ảo gần như không khớp (thiếu band KAMA trên replay). Median win hay bị 21:50/20:00 Friday cắt khi giá mới đi ~0.6–1R. Loss lớn (2018-01-05, 2018-02-06) là buy kéo 13h+ rồi trượt thêm sau mức stop ước. Asia PF 0.73 / Europe 0.79. Không xác minh được iCustom code ±2 trên replay — đừng đọc SMA20 như bằng chứng S2.

3. **Asia-London: phá range London rồi bị SL/time-stop trong ngày.** 1173 lệnh, PF 0.96, 907 lệnh Europe. Trên cửa sổ có M15 (2022-05+): win lớn 2023-05-05 sell close-break → TP 1.5R sạch; loss lớn 2022-11-28 / 2023-03-20 buy break rồi bị kéo ngược về phía kia Asia range (SL ~1R). Nhiều lệnh median thoát TIME_STOP 32 nến (~8h) ở 0.5–0.8R — không kịp 1.5R. Cờ “London < 08:00” trên replay **không dùng để kết luận EA vào sớm** (giả định GMT+2 có thể lệch); nhìn cụm entry 08:15–10:30 server.

4. **Donchian H4 faithful, chết ở NY và Friday flat.** 425/427 close-break N=20 đúng. 207 SL vs 114 TP. Europe +225 / NY −727 (PF 0.62). Case thua lớn hay là break H4 rồi nến NY/Asia sau đảo (2019-10-03 buy 20:00, 2019-02-27 sell 20:00 — sát Friday flatten). 87 Friday-flat. Close-break là thật; follow-through sau H4 không đủ trả 1.5R ngoài phiên Europe.

5. **PDBREAK EURUSD: phá PDH/PDL đúng, gần như không bao giờ tới TP.** 1090/1091 thesis_ok. 731 TIME_STOP / 190 Friday-flat / 34 TP / 128 SL. WR ~50% nhưng loser lớn hơn — continuation FX không đi 1.5R trong 24 H1. Chart: entry đúng nến close vượt prior-day, rồi sideway/mean-revert.

6. **M15 TrendPB tự khóa DD rồi im.** 721 lệnh chỉ trong 2018-01-02 → 2019-02-25 rồi hết; maxDD artifact ~8.02% = đúng trần lock 8%. PF 0.66. Portable không có M15 2018–19 nên case là H1 context + marker deal. Không kết luận EMA21 từ H1.

7. **Spread/flat cắt nhìn thấy trên chart, không phải “thiếu lệnh”.** SweepFade/GBB: hàng loạt exit đúng 21:50:00 hoặc 20:00 Friday, PnL nhỏ (±1–7 USD) dù cấu trúc đúng. Donchian/PDBREAK: Friday 20:00 và time-stop chiếm chỗ TP. Đây là lý do PF<1 nhìn từ hình, không phải parser.

8. **Việc Main cần nhìn (không tuyên bố edge, không holdout).** Mở `_cases.html` của SweepFade (cấu trúc OK, payoff không) và Donchian (break OK, NY/Friday giết). GBB xem `_overview.html` — equity bậc xuống, cụm daily-flat. Asia-London chỉ tin case từ 2022-05. TRENDPB/PDBREAK là phụ: một đứa chết lock, một đứa time-stop. Không nới HQ. Không Visual trên GUI Owner.
