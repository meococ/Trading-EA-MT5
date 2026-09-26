# Deep market research — day-boundary reversal complex (2026-09-18)

> **CORRECTED 2026-09-19**: deep-history event-level verification (M1 .hcc,
> 2010→2025) FALSIFIED the pierce-fade claim below — up-pierces CONTINUE
> (fade loses −2 to −7.7p, win 15–35%, all symbols all years). The verified
> mechanism is **roll-reopen gap reversion**, not sweep-fade. See
> `20260919_ROLL_GAP_REVERSION_DEEP_HISTORY.md`. The 00h unconditional drift
> leg below survives (+0.5–0.9p/day post-2016) but is weaker than the
> conditional gap mechanism. Treat all "fade PF 1.45–5.56" numbers here as
> withdrawn.

Status: **Stage-0 findings, chưa governed**. Data: MQ-Demo portable isolate,
M5 bars **2025-05→2026-09-10 only (~98k bars ≈ 16 months — the "2022" label
was wrong; copy_rates silently stopped at the stub-.hcc gap)**, ticks ~4 tuần
gần nhất. Method mới so với mọi probe trước: **conditional-vs-unconditional** —
đo thông tin signal thêm so với baseline cùng hour-of-week, signed theo
hướng trigger, entry tại next-bar-open (executable semantics).

## S1 — Opportunity map

Excursion tập trung tại server-15h (=13:00 GMT = US data window 8:30 ET)
và late-Friday — event-driven, không phải all-hours. Median-hour exc1h
~1.1–1.5p → cost/excursion >200% → đa số giờ không tradeable. Best hours
cost/exc 12–25%.

## S2 — Autocorrelation

Lag-1 âm nhẹ mọi symbol (-0.011~-0.027) — microstructure mean-reversion
ở 5 phút, không momentum. Lag 3–12 ≈ 0. Linear structure chết ở M5.

## S3/S4/S5 + day-boundary deep dive — FINDING CHÍNH

### Mechanism 1: Day-open sweep fade (conditional)

Bar(s) đầu ngày (00:00–00:30 server) pierce range 6h trước → FADE hướng
pierce, entry next-bar-open, hold 1–4h.

| Symbol | Events/wk | Signed drift 4h | PF (per-bar, 2h) | Win% |
|---|---|---|---|---|
| NZDUSD | 4.1 | -7.48p t=-9.14 | 5.56 | 84→73% |
| USDCHF | 4.3 | -5.80p t=-5.44 | 3.88 | 81→76% |
| AUDUSD | 3.2 | -7.08p t=-7.70 | 5.12 | 89→77% |
| GBPUSD | 2.7 | -7.56p t=-5.41 | 2.90 | 81→63% |
| USDCAD | 2.3 | -6.82p t=-6.75 | 5.00 | 85→81% |
| EURUSD | 1.6 | -5.07p t=-3.33 | 1.45 | 77→62% |
| USDJPY | 2.4 | -0.89p t=-0.28 | 1.71 | 56→68% |

- **6/7 symbol cùng chiều, split-half consistent, MỌI weekday đều âm**
  (không phải Monday-gap artifact). JPY ngoại lệ đúng logic kinh tế:
  00:00–01:00 server = 07:00–08:00 JST = home session JPY → flow thật,
  không phải stop-hunt.
- Executable: trigger-open vs next-open drift gần như nhau (-8.4 vs -7.6).
- Nhanh: phần lớn fade xong trong 1h (-5~-6p của tổng -6~-7.5p).
- Effect CÔ ĐẶC day-boundary: LDN 07:00 / NY 15:00 / dayHL sweep → không
  fade (null hoặc continuation). Không phải generic session-boundary.

### Mechanism 2: Early-Asia drift (unconditional, calendar)

Long tại 00:55 server, hold +1h. CẢ 7 SYMBOL dương:

| Symbol | PF | Win% | Mean |
|---|---|---|---|
| USDCHF | 3.94 | 75% | +2.76p |
| AUDUSD | 3.71 | 72% | +2.30p |
| NZDUSD | 3.48 | 70% | +2.26p |
| GBPUSD | 2.30 | 64% | +2.17p |
| USDJPY | 1.57 | 59% | +2.04p |
| EURUSD | 1.77 | 60% | +1.28p |
| USDCAD | 1.77 | 59% | +1.19p |

Là hour-of-week effect (baseline cùng giờ đã dương) — calendar mechanism
thuần, trade mọi ngày không cần trigger. Tương thích logic: 00:55–02:00
server = 07:55–09:00 JST = Tokyo-morning real flow.

### Cost tại window (tick-level, ~4 tuần thật)

Spread tại 00:00–02:00 server trên MQ-Demo: **p50 0.1–0.2p, p90 0.2–0.3p**
— phẳng như giờ liquid, không có rollover widening. Real RT cost ~0.5–1p.
Gross edge 5–7p → margin rộng.

### Cadence tổng hợp (GOAL floor 10/wk/symbol)

| Symbol | Fade/wk | Drift/wk | Tổng |
|---|---|---|---|
| USDCHF | 4.3 | 5 | ~9.3 |
| NZDUSD | 4.1 | 5 | ~9.1 |
| AUDUSD | 3.2 | 5 | ~8.2 |
| GBPUSD | 2.7 | 5 | ~7.7 |
| USDJPY | 2.4 | 5 | ~7.4 |
| USDCAD | 2.3 | 5 | ~7.3 |
| EURUSD | 1.6 | 5 | ~6.6 |

Nới fade window tới 00:00–02:00 (union) → +30–50% events ở một số symbol.
Tranches per-bar trong window đã được count trong số trên (mỗi qualifying
bar = 1 trade). Top symbols chạm ~9–11/wk — GẦN/ĐẠT GOAL floor lần đầu.

## Giải thích cơ chế (story, không phải bằng chứng)

00:00 server = day boundary + post-rollover liquidity vacuum. Bar đầu
ngày sweep qua range buổi tối = stop-hunt trên liquidity mỏng → Tokyo
open (07:00 JST) mang flow thật đảo ngược → fade. Sau đó early-Asia drift
tiếp tục theo hướng flow thật → leg 2.

## Caveats (thành thật)

- Bar-close probe — gap probe→governed đã đốt 2 lần; chỉ governed run
  quyết định. Giảm thiểu: entry next-bar-open đã executable.
- Fade leg và drift leg overlap thời gian (00:05–01:00 vs 00:55–02:00) —
  cùng một underlying event, trade count vs independence cần khai rõ
  trong prereg.
- n=78–340/symbol trên ~2 năm — đủ cho split-half/cross-asset consistency
  nhưng không lớn. Win% có decay nhẹ 2025→2026 (vẫn sống).
- Chưa thiết kế stop cho fade (stop-hunt có thể extend trước khi revert —
  adverse excursion cần đo trước khi mint).

## Kết luận nghiên cứu

Đây là **conditional edge đầu tiên được verify trên feed này** sau 23
governed kills — và nó chỉ lộ ra khi đổi method (conditional-vs-baseline
+ signed direction + executable entry + cost-at-execution-hour). Mọi probe
trước đo unsigned/unconditional nên effect nằm ẩn trong hour baselines.

Hướng duy nhất đáng mint EA: **day-boundary reversal complex** —
fade leg + drift leg, single-symbol sleeves, top symbols NZD/CHF/AUD.
