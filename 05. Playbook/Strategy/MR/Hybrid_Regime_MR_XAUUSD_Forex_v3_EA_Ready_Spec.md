# SPEC HỆ THỐNG v3 — EA-READY
## Regime-Gated Mean-Reversion trên XAUUSD & EURUSD (H1)

**Phiên bản:** v3.0 — thay thế hoàn toàn v1/v2
**Ngày:** 17/07/2026
**Người thực hiện:** Linh (deep research 5 nhánh song song, adversarial verification)
**Trạng thái:** Spec chốt để bắt đầu Phase 0. Mọi tham số có default + grid + nhãn nguồn gốc (§13).

---

## 0. Thay đổi nền móng so với v1/v2 — và lý do

Deep research (17/07/2026) đã kiểm chứng các claim nền của v1/v2. Kết quả buộc đổi thesis:

| Claim cũ (v1/v2) | Verdict | Bằng chứng chính |
|---|---|---|
| Gold Hurst ≈ 0.405 (anti-persistent) | ❌ Không phải stylized fact | Đa số nghiên cứu: H ≈ 0.5–0.6; anti-persistence chỉ theo regime/scale (Wang 2011; Mensi 2022; Urquhart 2016) |
| Gold half-life 60–90 ngày | ❌ Bác bỏ | Schwartz (1997, *J. Finance*): "no detectable mean reversion in gold"; Mejía Vega (2018): half-life ~14–16 **năm** |
| EURUSD half-life ~9 ngày | ❌ Bác bỏ (nhầm horizon) | PPP: 3–5 năm cho real FX (Rogoff 1996; ECB WP 1576); OU trên nominal daily ≈ 670 ngày; Chan: USDCAD ~115–260 ngày |
| VR < 1 (MR) ở short horizon FX | ❌ Bác bỏ | Liu & He 1991: VR > 1; Fong 1997, Chang 2004: không bác được random walk; VR<1 ở tick/minute = bid-ask bounce (Andersen-Bollerslev-Das 2001) |
| BIS 2025: $9.6T/ngày, spot 31% | ✅ Xác nhận | BIS Triennial 30/09/2025 (lưu ý: April 2025 có volume spike do tariff shock) |
| Intraday EURUSD có seasonality | ✅ Xác nhận | Breedon & Ranaldo (2013, *JMCB*): EUR giảm phiên sáng Âu, tăng phiên Mỹ; Sharpe ~1.3/0.9 sau cost (data 1997–2007 → rủi ro decay) |
| Lo 2002: Sharpe overstated tới ~65% | ✅ Xác nhận | Lo (2002, *FAJ*), nguyên văn abstract |
| Swap long gold rất âm | ✅ Xác nhận | ~−$55/lot/đêm (range −40 → −90), triple thứ Tư (IC Markets, Pepperstone, Exness) |
| Order Block codify được | ✅ Có 4 định nghĩa thật | LuxAlgo SMC, joshyattridge (Python ~1k sao), MQL5 article 23341 (07/2026). Nhưng KHÔNG có peer-review chứng minh edge |

**Thesis mới (trung thực với literature):**

> Gold và EURUSD ở daily gần như random walk — không được giả định "asset này mean-reverting". Edge (nếu có) là **giả thuyết có điều kiện**: (i) mean reversion *tạm thời theo regime* trên chuỗi đã detrend (Urquhart 2016; Auer 2016 — Hurst time-varying rules từng beat buy-and-hold), (ii) session seasonality EURUSD (Breedon-Ranaldo — anomaly intraday duy nhất trích dẫn được), (iii) cụm order S/R có cơ sở microstructure (Osler, FRBNY). Kẻ thù chính là **chi phí**: literature net-of-cost cho intraday FX reversal là tiêu cực nếu trade bừa. Hệ thống này chỉ đáng chạy tiền thật nếu vượt toàn bộ gates ở §10.

Mọi con số half-life/Hurst/z-threshold trong spec này là **internal calibration** (fit trên data của mình, trên object đã định nghĩa) — không phải "fact từ paper". Nhãn rõ ở §13.

---

## 1. Phạm vi & mục tiêu

- **Assets:** EURUSD (chính, chi phí thấp nhất thế giới — spot $3T/ngày), XAUUSD (phụ, chi phí cao, swap nặng — chỉ chạy nếu EURUSD baseline sống sót).
- **Timeframe:** Entry & quản lý trên **H1**. Bias/veto trên H4. Diagnostics (Hurst/VR) trên H4/D1. *(M15 bị loại khỏi v3: chi phí chiếm tỷ trọng lớn hơn trên biên độ nhỏ hơn, và các test thống kê không đủ power ở cửa sổ ngắn. Có thể thử lại ở v4 nếu H1 có edge dư dả.)*
- **Stack:** Python (research/backtest) → MQL5 (EA) với port-parity protocol (§11.3).
- **Risk:** 0.5%/trade, daily stop 1.5%, portfolio cap theo USD-bucket (§8).
- **Tiêu chí phê duyệt:** vượt Gates 0–5 (§10). Không vượt → không live, không "chỉnh thêm tí".

---

## 2. Dữ liệu & Timestamp/Leakage Protocol

### 2.1. Dữ liệu bắt buộc
- Bid/ask M1 (hoặc tick nếu có) từ **chính broker sẽ chạy live**; nguồn thứ 3 (Dukascopy/Tickstory) chỉ dùng để cross-check robustness.
- Period: 2015–nay (in-sample 2015–2022, OOS 2023–nay). OOS chứa giai đoạn gold trending mạnh 2024–2026 — đây là **stress test có chủ đích** cho regime filter; chấp nhận ít trades gold trong OOS, bù bằng min-trades tính trên toàn period (§10).
- Economic calendar có timestamp UTC, importance flag, currency (USD, EUR).
- Broker specs: contract size, tick value, swap long/short + ngày triple swap, commission — lưu thành `costs.yml` có ngày cập nhật.

### 2.2. Timestamp protocol (chống look-ahead — bắt buộc, audit được)
1. Mọi feature chỉ dùng **bar đã đóng**. Feature availability time = close time của bar đó.
2. Quyết định vào lệnh tại **open của bar kế tiếp** (H1). Backtest khớp giá open + slippage model, không khớp giá close của bar tín hiệu.
3. Mọi tham số rolling (μ, σ, ATR, ADX, half-life, percentile) tính trên cửa sổ **kết thúc ở bar t−1** khi quyết định tại open bar t.
4. H4 bias/veto dùng **bar H4 đã đóng gần nhất** (không dùng H4 đang chạy).
5. Trong backtest bar-based: nếu SL và TP cùng chạm trong 1 bar → **giả định SL chạm trước** (worst-case). Chỉ bỏ giả định này khi chạy tick data.
6. News filter dùng thời điểm **lịch công bố trước** (scheduled time), không dùng thời điểm biết kết quả.
7. Log `feature_time`, `decision_time`, `execution_time` cho từng lệnh — file audit riêng.

---

## 3. Định nghĩa Alpha (object đúng để đo mean reversion)

**Không fit OU trên price level** (Schwartz 1997; Avellaneda & Lee 2010: MR phải đo trên residual/stationary object). Bản retail 2-asset dùng "poor-man's residual":

```
D_t   = Close_t − SMA(Close, W)_t        # chuỗi detrend (H1, W bars)
sigma = StdDev(D, W)_t                   # độ lệch chuẩn của D
z_t   = D_t / sigma_t                    # z-score
```

- `W` default **100** H1 bars (grid 60–150). μ = SMA; σ tính trên D, không phải trên returns.
- **Half-life estimate** (Chan): hồi quy `ΔD_t = a + λ·D_{t−1} + ε`, `HL = −ln(2)/λ` (đơn vị: H1 bars), rolling window = W. Đây là half-life **của chuỗi D** (window-induced — trung thực mà nói, W quyết định phần lớn HL). Vai trò: gate + time-stop, không phải "đặc tính asset".
- **HL gate:** chỉ trade khi `λ < 0` và HL ∈ **[4, 24]** bars với XAUUSD, **[4, 48]** bars với EURUSD (internal calibration, grid ±50%). HL ngoài range = chuỗi đang gần random walk hoặc reversion quá chậm so với ngân sách swap.

**Chuẩn giá & công thức (pin để đạt parity §11.3):** mọi giá = **Bid close** (chuẩn bar MT5). ATR(14) = Wilder RMA (khớp `iATR`). ADX(14) = `iADX` (Wilder). SMA đơn giản. σ = StdDev với ddof=0 trên D. Python PHẢI khớp định nghĩa MT5 — nhiều lib (pandas_ta, talib mode khác) dùng smoothing khác, lệch đủ để lật gate ADX 23 và phá parity §11.3.
**Guards tính toán:** `σ_t−1 = 0` hoặc `λ ≥ 0` → không tính signal bar đó.

---

## 4. Regime Filter Ensemble

Nguyên tắc: ADX + ATR percentile là **gate chính** (đủ power ở mọi cửa sổ); Hurst/VR là **diagnostics tuần** trên H4/D1 (nơi đủ sample), không phải gate per-bar. Lý do: VR test trên cửa sổ 100–200 bars bị size distortion + underpowered nghiêm trọng (Lo-MacKinlay 1989; Kim 2006/2009) — kết luận verify, không thương lượng.

### 4.1. Gates per-bar (H1, tính trên bar đóng)
| Gate | Điều kiện | Default | Grid |
|---|---|---|---|
| Trend veto H1 | ADX(14) < X | 23 | 20–26 |
| Trend veto H4 | ADX(14) trên H4 < Y | 28 | 24–32 |
| Vol băng thông | ATR(14) percentile trong 250 bars ∈ [lo, hi] | [25%, 75%] | lo 15–35, hi 65–85 |
| Spread guard | spread hiện tại ≤ 1.5 × p75 bảng chi phí (§9) | on | on/off |

### 4.2. Diagnostics tuần (không gate per-bar)
- **VR test:** `arch.unitroot.VarianceRatio(D, lags=q, robust=True)` trên H4 với T ≥ 512 bars, q ∈ {2, 4}; dùng thống kê robust M2 (đã sửa erratum RFS 1990 nếu tự viết — khuyến nghị dùng arch, đừng tự viết). Joint inference: Chow-Denning, không đọc từng p-value rời.
- **Rolling Hurst (DFA):** window ≥ 512 bars H4/D1, chỉ để dashboard theo dõi regime drift. **Không** dùng ngưỡng 0.45/0.48 trên 100–200 bars như v1/v2 — mức nhiễu ±0.1 khiến ngưỡng đó vô nghĩa.
- **Rule giảm size theo diagnostics (định lượng):** đánh giá Chủ nhật 20:00 UTC, trên H4 với T = 512 bars: tuần tính là "trending" nếu VR(2) > 1 VÀ VR(4) > 1 VÀ Chow-Denning joint p < 0.05. **4 tuần "trending" liên tiếp → size 50%** asset đó; khôi phục 100% sau 2 tuần liên tiếp không thỏa điều kiện.

### 4.3. Session filter (định nghĩa UTC, tránh bug DST)
- **EURUSD:** entry cho phép khi open time của bar vào lệnh ∈ **[07:00, 16:00) UTC** (khoảng nửa mở).
- **XAUUSD:** entry ∈ **[12:00, 20:00) UTC** (LDN–NY overlap + NY sáng).
- Quản lý vị thế (SL/TP/trailing/time-stop/forced close) chạy **24/5** — session chỉ giới hạn entry, không dừng quản lý lệnh ngoài giờ.
- EA input `ServerToUTCOffsetWinter/Summer` + bảng DST (US/EU lệch nhau ~2-3 tuần tháng 3 và 10-11) — hard-code lịch DST năm hiện hành, update mỗi năm. **Không** viết session theo giờ server rồi quên DST — bug kinh điển.
- *(Optional, variant test riêng)* Seasonality overlay theo Breedon-Ranaldo: chỉ nhận signal short EURUSD trong phiên sáng Âu, long trong phiên Mỹ. Nhãn: hypothesis có citation nhưng data gốc 1997–2007, decay risk cao — bật/tắt qua grid, giữ chỉ khi cải thiện OOS.

### 4.4. News filter
- Block entry: sự kiện high-impact USD/EUR trong **[t−45', t+30']** với XAUUSD, **[t−30', t+15']** với EURUSD (engineering default, grid on/off).
- Flatten rule: trước FOMC/NFP/CPI, nếu đang có lệnh PnL < +0.5R (đo tại bar close) → forced close tại **open của bar H1 cuối cùng bắt đầu trước cửa sổ block** (grid on/off).

---

## 5. Biến thể A — Core Regime-Gated MR (bản chính, 100% codifiable)

### 5.1. Entry
Tại open bar t (mọi điều kiện trên bar ≤ t−1):
```
LONG  khi: z ≤ −Z_entry  VÀ tất cả gates §4 pass  VÀ HL gate §3 pass
SHORT khi: z ≥ +Z_entry  VÀ tất cả gates §4 pass  VÀ HL gate §3 pass
```
- `Z_entry` default **2.0** (grid 1.6–2.4).
- 1 lệnh/asset/lúc. Không add, không grid, không martingale. **Không partial close ở bất kỳ đâu trong v3.**
- **Re-entry cooldown:** sau khi thoát lệnh (bất kỳ lý do), không entry mới trên asset đó cho đến khi z đã đóng ≥ 1 bar bên trong ±Z_entry.
- Kỳ vọng tần suất: ~1–3 setups/tuần/asset sau filters — **phải verify trong backtest**; nếu < 0.5/tuần → gates quá chặt, xem lại grid (và ghi nhận vào trial log §10.4).

### 5.2. Stop Loss (luôn nằm trên server)
```
SL = Entry ∓ K_sl × ATR(14)_t−1     # default K_sl = 2.0, grid 1.5–2.5
```

### 5.3. Exits — bảng ưu tiên duy nhất (không mơ hồ)
Tại entry, tính và ĐÓNG BĂNG: `mu_e = SMA_t−1`, `sig_e = sigma_t−1`, `R = |Entry − SL|`, `HL_e`.
```
TP_mean  = mu_e ∓ 0.2 × sig_e                        # buffer trước mean
TP_cap   = Entry ± 1.5 × R                           # trần RR 1:1.5
TP       = mức GẦN entry hơn giữa TP_mean và TP_cap  → đặt limit trên server
Validity : nếu TP_mean không cách entry ≥ max(StopsLevel broker, 2×spread p50)
           theo hướng có lợi (vd giá gap qua mean lúc khớp) → dùng TP_cap
Trailing : đánh giá tại BAR CLOSE; khi PnL ≥ +0.8R (đo tại close):
           SL_new = Close_t ∓ 1.2 × ATR(14)_t−1 (rolling, không đóng băng)
           chỉ dời theo hướng có lợi (monotonic), tối đa 1 lần/bar
Time-stop: effective_ts = min( ceil(k_ts × HL_e), số bars đến night-cap §5.4 )
           k_ts default 2.0 (grid 1.5–3.0)
           đủ bars → đóng TOÀN BỘ vị thế tại open bar kế tiếp
```

**Thứ tự ưu tiên exit (EA là state machine — đúng thứ tự này, không ngoại lệ):**

| # | Rule | Thời điểm thực thi |
|---|---|---|
| 1 | SL / TP server | intrabar, luôn sống |
| 2 | Daily stop / equity guard (§8) | check tại mỗi bar close + mỗi order event → market close ngay |
| 3 | Forced close theo lịch: night-cap, đêm triple, thứ Sáu (§5.4), news flatten (§4.4) | open của bar H1 cuối cùng bắt đầu trước trigger (buffer ≥ 5 phút) |
| 4 | Time-stop | open của bar kế khi đủ effective_ts |
| 5 | Trailing (chỉ sửa SL, không đóng lệnh) | bar close |

**Hình học TP — cảnh báo biết trước:** σ_D (std của detrend, W=100) và ATR(14) khác scale. Với chuỗi gần random walk, σ_D/ATR ≈ 3–4 → khoảng tới TP_mean (~1.8σ) hầu như luôn XA hơn TP_cap (3×ATR khi K_sl=2) → **TP_cap sẽ binding phần lớn, RR khi TP chạm ≈ 1:1.5 cố định**. WR/RR mục tiêu (55–68% / ~1:1–1.5) là **hypothesis phải đo, không phải cam kết**. Deliverable Phase 1 bắt buộc: phân bố thực nghiệm σ_D/ATR14 theo asset và theo W; nếu TP_cap binds > 90% → đơn giản hóa TP = 1.5R cố định, bỏ TP_mean. **Không** đòi RR 1:2.5–3 (đó là hệ reversal khác, không thuộc spec này).

### 5.4. Holding caps theo ngân sách swap (số liệu verify §9)
- **Định nghĩa "đêm":** 1 đêm = 1 lần rollover bị tính swap. Rollover = **00:00 giờ server** (broker GMT+2/+3 → trùng 5pm NY). Fri→Mon tính theo số rollover thực tế bị charge (đọc `costs.yml`).
- **XAUUSD:** tối đa **2 đêm**. Nếu đêm kế là đêm triple (`costs.yml: triple_day`, thường thứ Tư) và PnL < +0.3R → forced close (rule #3 §5.3). **Thứ Sáu:** không giữ gold qua weekend nếu PnL < +0.3R (gap risk) — cùng cơ chế forced close.
  - Ví dụ: tài khoản $10k, risk $50, ATR H1 ≈ $8 → SL = $16/oz → size = 50/(16×100) = 3.125 oz = 0.031 lot; swap long −$55/lot/đêm → −$1.72/đêm ≈ **−0.034R/đêm**, đêm triple ≈ −0.10R.
- **EURUSD:** tối đa **5 đêm**. Ví dụ cùng giả định: ATR H1 ≈ 14 pips → SL = 28 pips → size = 50/(0.0028×100 000) = **0.178 lot**; swap long −$8/lot/đêm → −$1.43/đêm ≈ **−0.029R/đêm**.
- Backtest trừ swap đúng ngày, đúng hệ số triple, đọc từ `costs.yml` — không hard-code thứ trong tuần.

---

## 6. Biến thể B — Optional: OB Confluence Filter (đã codify, off theo mặc định)

Chỉ test **sau khi** Variant A có baseline. Nhận định trung thực: không có peer-review nào chứng minh OB có edge (LuxAlgo tự ghi chú "no supporting data"; Bajgrowicz & Scaillet 2012: technical rules không còn OOS edge sau costs); cơ chế S/R clustering có cơ sở microstructure (Osler, FRBNY). Vậy OB là **filter cần chứng minh incremental value**, không phải edge độc lập.

Định nghĩa codified (theo joshyattridge + displacement filter từ MQL5 article 23341):
```
Swing:      fractal đối xứng, swing_length = 5 (5 bars trước + 5 sau; chấp nhận lag 5 bar — KHÔNG dùng swing chưa xác nhận)
Trigger:    close bar t > swing high gần nhất (bull) — mỗi swing chỉ sinh 1 OB
Displace:   body bar breakout ≥ 1.5 × avg body(20)      # engineering default, grid 1.2–2.0
OB candle:  bar có LOW THẤP NHẤT trong (swing bar, breakout bar)
Zone:       [low, high] đầy đủ của OB candle
Bear OB:    đối xứng ngược
Invalidate: Bid close vượt biên XA của zone (bull OB: close < low zone;
            bear OB: close > high zone) → xoá
Queue:      giữ tối đa 5 zone/side; tuổi tối đa 200 bars (bổ sung của mình — các nguồn gốc chỉ dùng queue, không dùng age)
Entry B:    điều kiện Variant A  VÀ  Bid close của bar t−1 nằm trong [low, high] zone cùng chiều
```
Tiêu chí giữ B: cải thiện net expectancy VÀ DSR trên OOS so với A. Không cải thiện → bỏ, không tiếc.

---

## 7. Những thứ CỐ TÌNH loại khỏi v3 (descope có lý do)

- **HMM regime:** hoãn đến v4. Lag + label-switching khi retrain rolling + khó port MQL5. ADX/ATR ensemble đủ cho baseline.
- **Full residual factor model (Avellaneda-Lee):** xác nhận đúng về lý thuyết, nhưng equilibrium gold~DXY/real-rates là quan hệ monthly, đã structural break (~2008) và residual **ngừng mean-revert từ 2022** (nguồn §14). Không đáng độ phức tạp cho hệ retail 2-asset. Giữ "poor-man's residual" §3.
- **M15 entry:** loại (lý do §1). **ML models:** chỉ sau khi baseline rule-based qua OOS. **Momentum overlay cuối phiên** (Baltussen 2021): ghi nhận là lý do tránh fade cuối phiên Mỹ — đã phản ánh trong session filter, không build module riêng.

---

## 8. Risk & Portfolio

- **Per trade:** 0.5% (0.3% trong 3 tháng live đầu). **Sizing:** `lots = risk_$ / (SL_dist_giá × contract_size)` — SL_dist theo đơn vị giá; contract_size = 100 (XAUUSD), 100 000 (EURUSD); trong MQL5 tổng quát hóa bằng `tick_value/tick_size`. Làm tròn **xuống** theo lot step; nếu < min lot → bỏ signal. Kelly: KHÔNG dùng cho đến khi có ≥ 6 tháng live edge net-of-cost dương.
- **Daily stop:** PnL ngày = (equity hiện tại − equity tại mốc 00:00 server) / equity mốc, **tính cả floating**. ≤ −1.5% → market-close toàn bộ + khóa entry đến 00:00 server kế. (Mốc ngày = 00:00 server — thống nhất mọi nơi, trùng thời điểm rollover.)
- **USD-bucket rule (concrete):** long XAUUSD và long EURUSD đều là short-USD → cùng bucket. Risk bucket = tổng risk các lệnh cùng bucket × **1.5**. Portfolio cap = **2.5%** (đặt sẵn cho lúc mở rộng ≥ 3 assets; với 2 assets, constraint binding thực tế là bucket + max lệnh). Tối đa 2 lệnh cùng bucket. Rolling correlation 60 ngày (D1 returns) |ρ| > 0.6 → lệnh thứ hai size 50%.
- **Equity guards:** DD từ đỉnh equity −8% → half size **cho đến khi equity lập đỉnh mới**; −12% → dừng hệ thống, post-mortem (khớp ngưỡng MaxDD MC §10).
- **Prop mode:** risk 0.25%, daily stop 1.2%; tắt XAUUSD nếu spread/commission của prop lệch > 30% so với `costs.yml`.

---

## 9. Cost Model (số verify 07/2026, nguồn §14 — cập nhật `costs.yml` mỗi quý)

**Đơn vị:** XAUUSD tính bằng **USD/oz** (1 lot = 100 oz; $0.01 = $1/lot). TUYỆT ĐỐI không dùng "pip" cho gold (Exness định nghĩa pip=0.01, hãng khác 0.1 — lệch 10 lần). EURUSD: 1 pip = 0.0001 = $10/lot.

| Tham số (raw/ECN + $7 RT commission) | XAUUSD | EURUSD |
|---|---|---|
| Spread p50 / p75 / p90 | $0.12 / $0.20 / $0.35 per oz | 0.1 / 0.2 / 0.4 pip |
| Spread news tail | $0.80–2.00 | 1–3 pips |
| Slippage adverse p50 / p90 / news | $0.05 / $0.30 / $0.50–2.00 | 0.0–0.1 / 0.2 / 1–3 pips |
| Commission round-turn / lot | $7 | $7 |
| Swap long / short per lot/đêm | **−$55** (−40→−90) / +$20 (dùng 0 nếu conservative) | −$8 / +$2.5 |
| Triple swap | Thứ Tư ×3 | Thứ Tư ×3 |

- Backtest chạy 3 kịch bản: **p50, p75, p90**. Gate tính trên p75; p90 phải không âm (§10).
- Swap model theo cơ chế, không hard-code: `swap_long ≈ −(SOFR + 1–3%) × price × 100 / 360` — tự cập nhật khi rates/giá gold đổi.
- Standard account (không commission): XAUUSD spread $0.25–0.35, EURUSD 0.9–1.1 pip — chạy như sensitivity, không phải baseline.

---

## 10. Backtest & Validation Gates (tuần tự, fail gate nào dừng gate đó)

**Gate 0 — Sanity:** ≥ **300 trades/asset** toàn period; setup xuất hiện ở ≥ 2 vol-regime khác nhau; không có năm nào chiếm > 40% tổng PnL.

**Gate 1 — Net-of-cost:** tại p75 costs: **PF ≥ 1.25** và **expectancy ≥ 0.08R**; tại p90: expectancy > 0. (Mục tiêu đẹp: PF ≥ 1.35, exp ≥ 0.15R — nhưng gate là gate.)

**Gate 2 — Robustness:** walk-forward ≥ 6 folds, ≥ 60% folds dương; lân cận tham số ±20% giữ ≥ 70% hiệu suất; bật/tắt news filter không lật dấu expectancy.

**Gate 3 — Inference (chống overfit — lý do tồn tại của gate này: mình sẽ thử hàng trăm config):**
- **Trial log bắt buộc:** MỌI config đã chạy được ghi vào registry (kể cả config bỏ đi). N trials là input của DSR.
- **DSR ≥ 0.95** (Bailey & López de Prado 2014 — tự implement ~100 dòng, validate với ví dụ số trong paper; KHÔNG dùng PSR của quantstats thay thế vì nó không deflate theo N).
- **PBO ≤ 0.25** qua CSCV S=16 (vendor `pypbo` hoặc tự viết; CPCV dùng `skfolio.model_selection.CombinatorialPurgedCV` với purge/embargo).
- **SPA** (`arch.bootstrap.SPA`) p < 0.10 cho family config đã thử vs benchmark zero-return.

**Gate 4 — Monte Carlo:** block-bootstrap trade sequence ≥ 1000 paths; **MaxDD 95th percentile ≤ 12%**; median recovery < 6 tháng.

**Gate 5 — Forward:** demo 4–6 tháng (Python + MT5 API); live-paper signal divergence < 5%; **median slippage rolling 20 lệnh ≤ budget p75** (cùng định nghĩa với guard §11.2).

**Reporting bắt buộc mỗi build:** net expectancy (R), PF, WR, **Sharpe hiệu chỉnh autocorrelation** (Lo 2002 — dùng `quantstats.smart_sharpe` hoặc tự tính; cấm annualize √252 trần), DSR, PBO, Calmar, CVaR95, MaxDD (MC-95th), turnover, avg holding (bars), swap paid/trade, số trades theo năm/phiên, stability khi bật/tắt từng filter.

**Manual review:** 80–120 setups XAUUSD xem tay trên chart (hiểu variance + train psychology) — chạy song song trong Phase 2, không phải gate thống kê.

**Tool stack:** pandas/numpy, backtest engine event-driven tự viết hoặc vectorbt (nếu vectorbt: viết test chứng minh không leak — fill tại open bar sau), `arch` (VR + SPA/RealityCheck/StepM/MCS), `skfolio` (CPCV), `quantstats` (reporting), DSR/PBO tự viết theo paper.

---

## 11. Execution & Live Guards

### 11.1. Execution
- Entry: market order tại open bar tín hiệu +1, có **slippage guard**: nếu spread hiện tại > 1.5×p75 hoặc giá quote lệch khỏi open của bar > 0.5×spread p75 → hủy, không đuổi giá.
- SL/TP: đặt server-side ngay khi fill. Trailing sửa SL qua OrderModify, tần suất tối đa 1 lần/bar đóng.
- Requote/reject: retry tối đa 2 lần trong 5s, sau đó bỏ signal, log lại.

### 11.2. Kill-switches (EA tự thực thi)
- Daily stop (định nghĩa §8) → flat + khóa entry đến 00:00 server.
- **Median** slippage rolling 20 lệnh > 2× budget p75 → size 50%, alert; **khôi phục** khi median rolling 20 lệnh ≤ 1× p75.
- Diagnostics "trending" 4 tuần liên tiếp (rule định lượng §4.2) → size 50% asset đó; khôi phục theo §4.2.
- Equity −8%/−12% từ đỉnh → half/stop; điều kiện khôi phục theo §8.
- Lỗi dữ liệu (gap mở bar > 4×ATR(14), spread ≤ 0, thiếu calendar) → không entry bar đó (quản lý lệnh mở vẫn chạy).

### 11.3. Port-parity protocol (Python → MQL5 — chỗ EA chết nhiều nhất)
1. Python export signal log chuẩn hóa (timestamp UTC, asset, direction, z, ATR, SL/TP levels).
2. MQL5 EA chạy cùng data (strategy tester + demo) export log cùng format.
3. So khớp tự động: **≥ 95% signals trùng** (lệch cho phép: 1 bar hoặc làm tròn giá); mọi lệch phải giải thích được (rounding, tick vs bar).
4. Chạy song song demo 4–8 tuần: Python paper vs EA demo — divergence PnL < 5%.
5. Chưa đạt parity → chưa được live. Không có ngoại lệ.

---

## 12. Roadmap (người có job full-time, dành ~6–10h/tuần cho dự án)

| Phase | Nội dung | Thời gian | Deliverable |
|---|---|---|---|
| 0 | Data pipeline (bid/ask M1, calendar, costs.yml), timestamp protocol, cost engine | 3–4 tuần | Data dictionary + cost engine + leakage checklist |
| 1 | Variant A trên EURUSD: alpha + gates + backtest engine | 4–6 tuần | Baseline v1 + trial registry + báo cáo σ_D/ATR (§5.3) |
| 2 | Validation Gates 0–4 + XAUUSD + manual review 80–120 setups | 6–8 tuần | Validation report (đủ metrics §10) |
| 3 | Forward demo Python qua MT5 API (chạy nền, song song việc khác) | 4–6 tháng | Forward log + divergence report |
| 4 | Port MQL5 + parity protocol §11.3 | 6–8 tuần | EA + parity report |
| 5 | Live 0.3% risk, review 90 ngày | 3 tháng | Go/no-go scale |

**Tổng: ~9–14 tháng.** Phase 3 chạy nền nên tổng lịch không phải cộng dồn tuyến tính. Điều kiện dừng sớm (đỡ tốn đời): Variant A EURUSD fail Gate 1 ở p75 sau grid hợp lệ → dừng dự án MR, giữ lại infrastructure (data pipeline + validation harness dùng được cho mọi strategy sau).

---

## 13. Parameter Registry (trích các tham số chính)

| Tham số | Default | Grid | Nhãn nguồn gốc |
|---|---|---|---|
| W (window μ, σ, HL) | 100 H1 bars | 60–150 | Internal calibration |
| Z_entry | 2.0 | 1.6–2.4 | Internal calibration |
| K_sl (×ATR14) | 2.0 | 1.5–2.5 | Engineering default |
| TP buffer | 0.2σ | 0.1–0.3σ | Engineering default |
| TP cap | 1.5R | 1.2–1.8R | Nhất quán triết lý MR |
| Trailing activate / dist | +0.8R / 1.2×ATR | ±25% | Engineering default |
| Time-stop k_ts (bị chặn bởi night-cap, §5.3) | 2.0 | 1.5–3.0 | Chan (HL làm holding budget) |
| Re-entry cooldown | z về trong ±Z_entry ≥ 1 bar | fixed | Engineering default |
| Entry deviation guard | 0.5×spread p75 | ±50% | Engineering default |
| Gap guard (no-entry) | 4×ATR(14) | 3–6× | Engineering default |
| HL gate XAU / EUR | [4,24] / [4,48] bars | ±50% | Internal calibration + swap budget |
| ADX H1 / H4 veto | 23 / 28 | 20–26 / 24–32 | Engineering default |
| ATR percentile band | [25,75]% /250 bars | ±10 | Engineering default |
| Session XAU / EUR (UTC) | 12–20h / 7–16h | ±1h | BIS liquidity + engineering |
| News window XAU / EUR | −45/+30' / −30/+15' | on/off | Engineering default |
| Hold cap XAU / EUR | 2 / 5 đêm | fixed | Swap verify (§9) |
| OB: swing / displace / age | 5 / 1.5× / 200 bars | §6 | Codified sources + bổ sung riêng |
| Risk / daily / bucket ×, cap | 0.5% / 1.5% / 1.5, 2.5% | fixed | Chính sách risk |
| Gates | §10 | fixed | Bailey-LdP, White/Hansen, Lo |

Quy tắc grid: tổng số config thử phải ghi vào trial registry — DSR sẽ trừng phạt việc thử nhiều, đó là tính năng, không phải lỗi.

---

## 14. References (verify 17/07/2026)

**Thị trường & microstructure:** BIS Triennial 2025 — [press](https://www.bis.org/press/p250930.htm), [commentary](https://www.bis.org/statistics/rpfx25_fx.htm) · Breedon & Ranaldo 2013 ([SNB WP](https://www.snb.ch/public/asset/en/www-snb-ch/publications/research/working-papers/2011/working_paper_2011_04/publications0_en/working_paper_2011_04.n.pdf)) · Baltussen et al. 2021 ([JFE](https://www.sciencedirect.com/science/article/abs/pii/S0304405X21001598)) · Osler, FRBNY ([SR125](https://fraser.stlouisfed.org/files/docs/publications/frbnysr/frbny_sr125.pdf))
**MR/Hurst/half-life:** Schwartz 1997 ([PDF](https://roycheng.cn/files/papers/paper_schwartz_1997.pdf)) · Mejía Vega 2018 ([DOI](https://doi.org/10.1186/s13662-018-1718-4)) · Urquhart 2016 ([DOI](https://doi.org/10.1080/1351847x.2016.1204334)) · Auer 2016 ([RePEc](https://ideas.repec.org/a/eee/finlet/v16y2016icp255-267.html)) · Wang 2011 ([Physica A](https://www.sciencedirect.com/science/article/abs/pii/S0378437110009490)) · ECB WP 1576 ([PDF](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1576.pdf)) · EURUSD OU fit ~670d ([quant.SE](https://quant.stackexchange.com/questions/40477/modelling-eur-usd-rate-with-ornstein-uhlenbeck-model)) · Chan half-life workflow ([letianzj](https://letianzj.github.io/mean-reversion.html), [robotwealth](https://robotwealth.com/exploring-mean-reversion-and-cointegration-part-2/))
**VR & inference:** Lo & MacKinlay 1989 ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/0304407689900833)) · Kim 2006/2009 ([EconLett](https://ideas.repec.org/a/eee/ecolet/v92y2006i1p38-43.html), [FRL](https://ideas.repec.org/a/eee/finlet/v6y2009i3p179-185.html)) · Andersen-Bollerslev-Das 2001 ([JF](https://public.econ.duke.edu/~boller/Published_Papers/jf_01.pdf)) · erratum M2 ([note](https://mingze-gao.com/posts/lomackinlay1988/)) · Lo 2002 ([CFA](https://rpc.cfainstitute.org/research/financial-analysts-journal/2002/the-statistics-of-sharpe-ratios)) · DSR ([SSRN 2460551](https://ssrn.com/abstract=2460551)) · PBO ([SSRN 2326253](https://ssrn.com/abstract=2326253)) · `arch` ([docs](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-reference.html)) · `skfolio` CPCV ([docs](https://skfolio.org/generated/skfolio.model_selection.CombinatorialPurgedCV.html)) · `pypbo` ([GitHub](https://github.com/esvhd/pypbo)) · `quantstats` ([GitHub](https://github.com/ranaroussi/quantstats))
**Stat-arb & OB:** Avellaneda & Lee 2010 ([summary](https://hudson-and-thames-arbitragelab.readthedocs-hosted.com/en/latest/other_approaches/pca_approach.html)) · gold residual break ([WGC](https://www.gold.org/goldhub/research/qaurum-vs-us-real-rates-and-dollar-model), [substack](https://chinarbitrageur.substack.com/p/gold-has-shifted-gears)) · OB codified: [joshyattridge/smc](https://github.com/joshyattridge/smart-money-concepts), [LuxAlgo SMC](https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/), [MQL5 article 23341](https://www.mql5.com/en/articles/23341) · Bajgrowicz & Scaillet 2012 ([PDF](https://scaillet.ch/pdfs/BajSca.pdf))
**Chi phí:** [IC Markets swap/spread](https://www.icmarkets.com/global/en/trading-pricing/swap-rates) · [Pepperstone pricing](https://pepperstone.com/en/ways-to-trade/pricing/) + UK Costs & Charges PDF 06/2026 · [Exness specs](https://get.exness.help/hc/en-us/articles/17854173039388-Commodities) · [Myfxbook IC swaps](https://www.myfxbook.com/forex-broker-swaps/ic-markets/312) · [execution/slippage test](https://www.compareforexbrokers.com/our-methodology/execution-speeds/)

**Inspiration (không phải evidence):** các post X trong v1 (@thedelost, @SystematicPeter, @0xTria, @promisenakpan…) — giữ credit ý tưởng workflow, mọi con số đã thay bằng nguồn verify hoặc nhãn internal calibration.

---

*v3 do Linh tổng hợp từ deep research 5 nhánh (adversarial verification) + review v1/v2 + bản rà soát chuyên nghiệp do Mèo Cọc cung cấp (các claim chính của bản đó — BIS 2025, Lo 2002, DSR/PBO/SPA, order-flow microstructure — đã verify ✅; riêng số "look-ahead bias 3.8%" không tìm được nguồn nên không đưa vào spec).*
