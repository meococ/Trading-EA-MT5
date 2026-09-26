# COST_GEOMETRY_FEASIBILITY — VPA-P0/P1 (v2: lift-over-random gate)

Status: `P1_GATE_PASSED_WITH_KILLS / PLANNING_ONLY / NO_ECONOMIC_AUTHORITY`
Task: VPA-P0 + VPA-P1 (Lead) · Package: `03. EA Developer/EA_VolmanPA/`
Ngày soạn: 2026-09-20 · Người soạn: OpenCode worker (em) · Owner: Mèo Cọc
Revision v2 (2026-09-20): sửa cổng theo Lead review v1 — so sánh với **random
entry cùng geometry** (§3b) thay vì "trần 47.15%" không transfer được.

Mục đích: **cổng khả thi chi phí–hình học (cost-geometry) phải chạy TRƯỚC khi
viết bất kỳ setup detector nào.** Tài liệu này chỉ ra symbol/session nào
*thậm chí có thể* có lời với hình học Volman, và ngưỡng KILL rõ ràng.

---

## 1. Nguồn số liệu (đã đo trong repo, không suy diễn)

| Đại lượng | Nguồn | Ghi chú |
|---|---|---|
| Spread p50/p90 theo symbol (MQ-Demo, tick thật ~3–4 ngày) | `03. EA Developer/EA_LiquiditySweep/research/evidence/EURUSD_spread_evidence.json:13-14`, `.../EA_SessionDrive/research/evidence/GBPUSD_spread_evidence.json:13-14`, `.../USDJPY_spread_evidence.json:13-14`, `.../EA_BoundaryEdge/research/evidence/USDCHF_spread_evidence.json:13-14`, `.../EA_LiquiditySweep/research/evidence/XAUUSD_spread_evidence.json:13-14` | `tester_spread_mode: current`; đơn vị pips; XAU pip = 0.1 USD (`02. AlphaFactory/lab/data_plane.py:26-27`) |
| Slippage p90 round-turn (quote thật, latency 250 ms) | `EURUSD_slippage_evidence.json:16,17,31`; `GBPUSD_...:16,17,31`; `USDJPY_...:16,17,31`; `USDCHF_...:16,17,31`; `XAUUSD_...:16,17,31` | p90 buy + p90 sell |
| Commission bound dùng trong mọi screen | `EA_LiquiditySweep/research/evidence/COST_SOURCE_MANIFEST.json:39-49` (value 7.0, `assumed_conservative_bound`) | Broker quan sát = 0.00/deal nhưng mọi screen dùng bound $7/lot RT ≈ 0.7 pip |
| Cost unit chính thức của task packet | `02. AlphaFactory/tools/research_loop_engine.ps1:1970-2094` (schema `alphafactory_cost_source_manifest.v1`) | Đây là manifest mà `ea_research_loop.ps1` bắt buộc bind |
| Deploy-plane (FivePercentOnline-Real) | `04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:16-18` | EURUSD 0.0–0.1p all-day (0.8p lúc 00h roll); USDCHF 0.1–0.2p |
| ATR14 M5 + median M5 range | **Probe read-only tự tính** từ `02. AlphaFactory/lab/cache/<SYM>_M1_2010_2026.parquet`, 2016→2026, loại bar `suspect`, resample M1→M5 (chỉ bar đủ 5 phút), Wilder ATR14 | Script: `%TEMP%\opencode\atr_probe.py`; bảng dưới |

### 1.1 ATR14 M5 đo được (server clock, 2016→2026)

| Symbol | ATR14 M5 all (pips) | p25–p75 | ATR14 London (srv 10–12) | Median M5 range (London) |
|---|---|---|---|---|
| EURUSD | **3.43** | 2.36–4.88 | 4.39 | 4.6 |
| GBPUSD | **4.71** | 3.18–6.78 | 6.12 | 6.5 |
| USDJPY | **4.24** | 2.90–6.27 | 4.81 | 4.6 |
| USDCHF | **3.01** | 2.09–4.18 | 3.70 | 4.0 |
| USDCAD | **3.73** | 2.67–5.28 | 3.94 | 4.1 |
| AUDUSD | **3.11** | 2.36–4.13 | 3.63 | 3.5 |
| NZDUSD | **2.96** | 2.30–3.86 | 3.36 | 3.3 |
| XAUUSD | **10.62** (pips 0.1 USD) | 6.80–18.28 | 11.40 | 11.1 |

Ý nghĩa trực tiếp cho bracket Volman (`10 pip stop / 20 pip target`):
- EURUSD: stop = 2.9×ATR M5 (London); target 20p = 4.6×ATR M5.
- XAUUSD: 10p stop chỉ = 0.9×ATR M5 → **quá hẹp so với nhiễu bar**; bracket
  Volman trên vàng bắt buộc phải scale lại.

---

## 2. Công thức (tái sử dụng, đã verify trong repo)

Required win-rate tại PF mục tiêu `T`, payoff thực `b` (R), cost `k` (R):

```
reqW(T, b, k) = T(1+k) / ((b - k) + T(1+k))
```

Nguồn: `04. Memory/research/20260726_REDTEAM_FULL_REPO_REVIEW.md:218` (công thức
đã được validate ngược với chính số của repo: b=1.0586, k=0, T=1 → 48.58%,
khớp `04. Memory/do_not_repeat_failures.md:326`).

Cost all-in theo pips round-turn:

```
c_rt = spread(session) + commission_price + slippage_p90_rt
k    = c_rt / S          (S = stop distance, pips)
```

Bracket Volman baseline: `S = 10`, target `B = 2S = 20` → payoff danh nghĩa
`b = 2.0`. Nếu bracket bị cắt sớm (manual exit / scratch / trượt), `b` tụt và
mọi ngưỡng đổi — xem §5.

---

## 3. Bảng cost và required win-rate (research plane, c_rt p90 = conservative)

| Symbol | spread p50 | spread p90 | slip p90 RT | comm | c_rt p50 | **c_rt p90** | ATR M5 all | ATR London (srv 10–12) |
|---|---|---|---|---|---|---|---|---|
| EURUSD | 0.0 | 0.1 | 0.2 | 0.7 | 0.8 | **1.0** | 3.43 | 4.39 |
| GBPUSD | 0.0 | 0.1 | 0.3 | 0.7 | 0.85 | **1.1** | 4.71 | 6.12 |
| USDJPY | 0.2 | 0.3 | 0.4 | 0.7 | 1.1 | **1.4** | 4.24 | 4.81 |
| USDCHF | 0.1 | 0.2 | 0.2 | 0.7 | 0.9 | **1.1** | 3.01 | 3.70 |
| USDCAD | — | — | — | 0.7 | — | **NOT MEASURED** | 3.73 | 3.94 |
| AUDUSD | — | — | — | 0.7 | — | **NOT MEASURED** | 3.11 | 3.63 |
| NZDUSD | — | — | — | 0.7 | — | **NOT MEASURED** | 2.96 | 3.36 |
| XAUUSD | 3.0 | 4.5 | 2.83 | 0.7 | 5.12 | **8.03** | 10.62 | 11.40 |

Required WR cho `PF > 1.30` (x1) tại `b = 2.0` theo stop S:

| Symbol | c_rt p90 | S=8 | S=10 | S=12 | S=16 | S=20 | S=30 | S=40 |
|---|---|---|---|---|---|---|---|---|
| EURUSD | 1.0 | 43.8% | **42.9%** | 42.4% | 41.6% | 41.2% | 40.6% | 40.3% |
| GBPUSD | 1.1 | 44.3% | **43.3%** | 42.6% | 41.8% | 41.4% | 40.7% | 40.4% |
| USDJPY | 1.4 | 45.6% | 44.3% | **43.5%** | 42.5% | 41.9% | 41.1% | 40.6% |
| USDCHF | 1.1 | 44.3% | **43.3%** | 42.6% | 41.8% | 41.4% | 40.7% | 40.4% |
| USDCAD/AUDUSD/NZDUSD | n/a | — | — | — | — | — | — | — |
| XAUUSD | 8.03 | 72.3% | 66.2% | 62.0% | 56.6% | 53.3% | 48.8% | 46.5% |

Ngưỡng x2 (`PF ≥ 1.00`) tại `b = 2.0`: EURUSD cần ~40.0% (S=10) / 39.0% (S=20);
XAUUSD cần ~62.6% (S=10) / 51.9% (S=20) — vượt xa trần.

> **CORRECTION (Lead review v1, 2026-09-20).** So sánh `reqW` với "trần 47.151%"
> là **sai phương pháp**: 47.151% đo trên hình học ~1:1.06 / stop 8 pip của một
> family ICT khác, không transfer sang bracket 1:2. Baseline đúng cho bracket
> 1:2 là **random entry cùng geometry**: driftless thì `P(TP trước SL) =
> S/(S+T) ≈ 33%`. Do đó cổng được viết lại thành **required lift over random**
> và được đo bằng mô phỏng thật ở §3b. (Số liệu cũ giữ nguyên ở §3 như bảng
> tham chiếu cost/R.)

---

## 3b. Random-entry baseline — mô phỏng trên DESIGN 2016–2021

### 3b.1 Phương pháp

Script: `research/lab/vpa_random_baseline.py` (read-only với repo; đọc parquet
M1 cache, resample M5 chuẩn 5 bar, loại bar `suspect`). Semantics khớp
FEATURE_SPEC 2.15/2.16 và quyết định của Lead:

- signal bar = bar M5 đóng trong session; stop-entry = cực trị bar ± **1.0 pip**;
  lệnh có hiệu lực **V = 3 bar** M5; fill = `max(open, stop)` (long) trên **đường
  M1**, rồi dịch **bất lợi đúng bằng c_rt** (x1/x1.5/x2);
- SL = fill − S, TP = fill + 2S; phân giải trên M1, **adverse-first** nếu một bar
  M1 chứa cả hai mức;
- nếu chưa phân giải khi hết session → flag `unresolved_sess` và **tiếp tục**;
- nếu chưa phân giải khi qua **server midnight** → đóng tại close trước đó;
- nếu chưa phân giải khi tới **Friday 20:00 server** → đóng tại đó;
- session UTC: London = 05:00–11:00, NY = 11:30–17:30 (UK open 08:00 ±3h, US open
  14:30 ±3h); server = UTC + 2h/+3h (EU DST) như quy ước data plane;
- 12,000 mẫu/cell, seed `20260920`; c_rt p90 theo bảng §3 (EURUSD 1.0p,
  GBPUSD 1.1p, USDCHF 1.1p, USDJPY 1.4p).

### 3b.2 Bảng A — baseline tại cost x1

| Symbol | Sess | S | c(p) | fill% | WR% | b | exp R | reqW(b=2) | lift_nom pp | reqW(b_obs) | lift_badj pp | unres% | Fri% | mid% | p50bar | p90bar | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EURUSD | london | 8 | 1.0 | 51.7 | 29.8 | 1.99 | -0.108 | 43.8 | +14.0 | 43.9 | +14.1 | 26.2 | 0.1 | 0.1 | 10 | 38 | **PASS** |
| EURUSD | london | 10 | 1.0 | 51.7 | 31.0 | 1.96 | -0.083 | 42.9 | +12.0 | 43.5 | +12.5 | 36.2 | 0.3 | 1.0 | 16 | 57 | KILL |
| EURUSD | london | 12 | 1.0 | 51.7 | 32.0 | 1.91 | -0.068 | 42.4 | +10.3 | 43.5 | +11.5 | 45.4 | 0.7 | 2.5 | 22 | 75 | KILL |
| EURUSD | london | 16 | 1.0 | 51.7 | 33.9 | 1.76 | -0.064 | 41.6 | +7.7 | 44.9 | +11.0 | 60.7 | 2.2 | 7.9 | 38 | 120 | KILL |
| EURUSD | london | 20 | 1.0 | 51.7 | 36.5 | 1.59 | -0.050 | 41.2 | +4.7 | 46.9 | +10.4 | 71.3 | 4.0 | 14.6 | 54 | 145 | KILL |
| EURUSD | ny | 8 | 1.0 | 52.8 | 31.7 | 1.80 | -0.106 | 43.8 | +12.2 | 46.6 | +14.9 | 20.1 | 4.5 | 6.5 | 7 | 40 | **PASS** |
| EURUSD | ny | 10 | 1.0 | 52.8 | 33.6 | 1.67 | -0.093 | 42.9 | +9.3 | 47.6 | +14.0 | 27.2 | 6.2 | 12.2 | 11 | 56 | **PASS** |
| EURUSD | ny | 12 | 1.0 | 52.8 | 35.5 | 1.56 | -0.079 | 42.4 | +6.8 | 48.8 | +13.2 | 33.9 | 7.4 | 18.0 | 16 | 67 | KILL |
| EURUSD | ny | 16 | 1.0 | 52.8 | 38.4 | 1.37 | -0.074 | 41.6 | +3.2 | 51.4 | +13.0 | 46.0 | 9.8 | 29.6 | 27 | 82 | KILL |
| EURUSD | ny | 20 | 1.0 | 52.8 | 40.9 | 1.24 | -0.062 | 41.2 | +0.2 | 53.4 | +12.5 | 55.5 | 11.9 | 39.3 | 42 | 93 | KILL |
| GBPUSD | london | 8 | 1.1 | 55.4 | 29.8 | 2.00 | -0.106 | 44.3 | +14.4 | 44.3 | +14.5 | 11.7 | 0.0 | 0.0 | 4 | 17 | **PASS** |
| GBPUSD | london | 10 | 1.1 | 55.4 | 31.4 | 2.00 | -0.058 | 43.3 | +11.9 | 43.3 | +11.9 | 17.1 | 0.1 | 0.0 | 7 | 26 | **PASS** |
| GBPUSD | london | 12 | 1.1 | 55.4 | 32.0 | 1.99 | -0.041 | 42.6 | +10.6 | 42.7 | +10.7 | 22.3 | 0.1 | 0.1 | 10 | 34 | **PASS** |
| GBPUSD | london | 16 | 1.1 | 55.4 | 32.5 | 1.96 | -0.039 | 41.8 | +9.4 | 42.4 | +9.9 | 34.0 | 0.5 | 1.1 | 16 | 55 | KILL |
| GBPUSD | london | 20 | 1.1 | 55.4 | 32.8 | 1.89 | -0.050 | 41.3 | +8.5 | 42.8 | +9.9 | 45.6 | 1.1 | 3.8 | 25 | 80 | KILL |
| GBPUSD | ny | 8 | 1.1 | 57.1 | 28.8 | 1.88 | -0.166 | 44.3 | +15.4 | 45.9 | +17.1 | 12.9 | 3.1 | 2.3 | 3 | 17 | KILL |
| GBPUSD | ny | 10 | 1.1 | 57.1 | 30.9 | 1.81 | -0.126 | 43.3 | +12.4 | 45.9 | +15.0 | 17.7 | 4.0 | 4.8 | 5 | 30 | **PASS** |
| GBPUSD | ny | 12 | 1.1 | 57.1 | 32.9 | 1.73 | -0.096 | 42.6 | +9.8 | 46.4 | +13.5 | 22.2 | 4.9 | 8.3 | 8 | 46 | **PASS** |
| GBPUSD | ny | 16 | 1.1 | 57.1 | 35.8 | 1.55 | -0.079 | 41.8 | +6.1 | 48.4 | +12.6 | 31.9 | 7.3 | 16.5 | 14 | 63 | KILL |
| GBPUSD | ny | 20 | 1.1 | 57.1 | 38.7 | 1.39 | -0.063 | 41.3 | +2.7 | 50.6 | +11.9 | 41.4 | 9.2 | 25.4 | 22 | 75 | KILL |
| USDCHF | london | 8 | 1.1 | 49.5 | 28.9 | 1.99 | -0.136 | 44.3 | +15.4 | 44.4 | +15.5 | 30.4 | 0.1 | 0.1 | 13 | 45 | KILL |
| USDCHF | london | 10 | 1.1 | 49.5 | 30.8 | 1.94 | -0.093 | 43.3 | +12.5 | 44.0 | +13.2 | 41.7 | 0.7 | 1.4 | 20 | 66 | KILL |
| USDCHF | london | 12 | 1.1 | 49.5 | 32.2 | 1.89 | -0.070 | 42.6 | +10.5 | 44.1 | +12.0 | 51.8 | 1.3 | 3.4 | 28 | 87 | KILL |
| USDCHF | london | 16 | 1.1 | 49.5 | 35.7 | 1.68 | -0.042 | 41.8 | +6.2 | 46.3 | +10.6 | 68.0 | 3.3 | 10.9 | 49 | 135 | KILL |
| USDCHF | london | 20 | 1.1 | 49.5 | 39.3 | 1.48 | -0.023 | 41.3 | +2.0 | 49.1 | +9.8 | 78.6 | 6.0 | 21.3 | 70 | 157 | KILL |
| USDCHF | ny | 8 | 1.1 | 51.6 | 29.9 | 1.72 | -0.176 | 44.3 | +14.3 | 48.4 | +18.4 | 22.6 | 5.3 | 8.2 | 9 | 47 | **PASS** |
| USDCHF | ny | 10 | 1.1 | 51.6 | 32.1 | 1.58 | -0.157 | 43.3 | +11.2 | 49.6 | +17.5 | 30.9 | 7.0 | 14.9 | 13 | 64 | KILL |
| USDCHF | ny | 12 | 1.1 | 51.6 | 34.2 | 1.45 | -0.143 | 42.6 | +8.5 | 51.2 | +17.0 | 38.2 | 8.4 | 21.4 | 19 | 74 | KILL |
| USDCHF | ny | 16 | 1.1 | 51.6 | 37.9 | 1.25 | -0.116 | 41.8 | +4.0 | 54.1 | +16.2 | 51.7 | 11.3 | 35.1 | 35 | 89 | KILL |
| USDCHF | ny | 20 | 1.1 | 51.6 | 40.5 | 1.14 | -0.093 | 41.3 | +0.8 | 55.9 | +15.4 | 61.5 | 13.5 | 45.7 | 50 | 97 | KILL |
| USDJPY | london | 8 | 1.4 | 48.8 | 28.5 | 1.96 | -0.154 | 45.6 | +17.0 | 46.1 | +17.5 | 32.7 | 0.3 | 0.9 | 12 | 53 | KILL |
| USDJPY | london | 10 | 1.4 | 48.8 | 30.0 | 1.92 | -0.121 | 44.3 | +14.3 | 45.4 | +15.4 | 43.1 | 0.6 | 2.1 | 19 | 73 | KILL |
| USDJPY | london | 12 | 1.4 | 48.8 | 30.9 | 1.86 | -0.115 | 43.5 | +12.6 | 45.5 | +14.6 | 52.2 | 1.4 | 4.4 | 28 | 95 | KILL |
| USDJPY | london | 16 | 1.4 | 48.8 | 34.0 | 1.67 | -0.086 | 42.5 | +8.5 | 47.1 | +13.1 | 66.7 | 3.5 | 11.8 | 47 | 140 | KILL |
| USDJPY | london | 20 | 1.4 | 48.8 | 36.9 | 1.51 | -0.066 | 41.9 | +4.9 | 49.1 | +12.2 | 76.6 | 5.8 | 20.0 | 67 | 159 | KILL |
| USDJPY | ny | 8 | 1.4 | 50.8 | 29.9 | 1.73 | -0.172 | 45.6 | +15.6 | 49.5 | +19.6 | 23.4 | 4.7 | 8.2 | 7 | 47 | KILL |
| USDJPY | ny | 10 | 1.4 | 50.8 | 32.6 | 1.60 | -0.138 | 44.3 | +11.8 | 50.3 | +17.7 | 31.0 | 6.3 | 14.1 | 12 | 63 | KILL |
| USDJPY | ny | 12 | 1.4 | 50.8 | 35.0 | 1.51 | -0.105 | 43.5 | +8.6 | 50.9 | +16.0 | 38.0 | 7.9 | 20.0 | 18 | 73 | KILL |
| USDJPY | ny | 16 | 1.4 | 50.8 | 38.1 | 1.34 | -0.085 | 42.5 | +4.4 | 53.0 | +14.9 | 49.4 | 10.3 | 31.4 | 30 | 86 | KILL |
| USDJPY | ny | 20 | 1.4 | 50.8 | 40.4 | 1.25 | -0.067 | 41.9 | +1.5 | 54.1 | +13.8 | 58.4 | 12.3 | 40.4 | 43 | 94 | KILL |

- `reqW(b=2)`: required WR cho PF>1.30 tại x1 với payoff danh nghĩa 2.0R.
- `reqW(b_obs)`: required WR dùng **payoff thực đo được** (bao gồm cả nén do
  time-exit/midnight) — đây là con số trung thực cho PF thật.
- `lift_nom`/`lift_badj` = reqW tương ứng − WR baseline.
- `fill%` thấp (~49–57%) là đặc tính của stop-entry 1 pip ngoài bar với V=3;
  phần không fill không tính vào WR.

**Nhận xét quan trọng (ghi trước khi xem setup):**
1. Baseline WR tăng theo S nhưng b giảm mạnh — WR cao ở S lớn là do các lệnh
   **time-exit tại session end/midnight** được tính là "thắng nhỏ", không phải
   TP thật. Vì vậy phải luôn đọc kèm `b_obs`.
2. Ở mọi cell, expectancy random đều **âm** khi có cost (đúng kỳ vọng).
3. Required lift x1 thực tế cho EURUSD London S=8 là **+14.0pp (nominal)** /
   **+14.1pp (b-adjusted)**; tại x2 là +18.2pp (b-adj). Đây là thanh chuẩn thật
   của chiến dịch: setup phải thắng random đúng bracket ~14–18 điểm WR.
4. Prior repo families cho thấy **~0 lift** so với random cùng hình học
   (47.151% measured vs 48.58% zero-edge tại b≈1.06/stop 8p — REDTEAM:218-226),
   nên đây là yêu cầu cao và có thể falsify sạch.

### 3b.3 Chọn primary S cho EURUSD (chốt trước outcome)

**Quy tắc R_S (đặt trước khi chạy, áp dụng lên bảng 3b.2):**
> Chọn S tối thiểu hoá `lift_badj` tại x1, subject to:
> (a) `unresolved_sess ≤ 30%`; (b) `b_obs ≥ 1.85`; (c) `S ≥ 2×ATR14_M5(all)`
> của symbol (= 6.86 pips với EURUSD); hoà → chọn S nhỏ hơn.

Áp dụng cho EURUSD:
- London S=8: lift_badj 14.1; unres 26.2 ✓; b 1.99 ✓; S=8 ≥ 6.86 ✓ → **eligible**
- NY S=8: lift_badj 14.9; unres 20.1 ✓; b 1.80 ✗
- NY S=10: lift_badj 14.0; unres 27.2 ✓; b 1.67 ✗
- Các cell còn lại: KILL.

→ **Primary S = 8 pips; primary session = London (UK open ±3h); NY là session
thứ cấp với cùng S.** Lý do: cell duy nhất hội đủ cả ba ràng buộc; p50 phân giải
10 bar M5 (~50 phút), p90 38 bar (~3.2 giờ) — vẫn là horizon scalp trong ngày;
b_obs 1.99 gần như giữ trọn bracket 2R.

`ASSUMPTION:` baseline dùng c_rt p90 all-hours; nếu cost per-session đo được thấp
hơn thì các cell bị KILL sát ngưỡng (GBPUSD NY S=8 nominal 15.4, USDCHF London
S=8 15.4, USDJPY NY S=8 15.6) có thể được xét lại bằng một prereg mới, không
phải rescue trong cùng cell.

---

## 4. Phán quyết cổng (lift-over-random, falsifiable)

**KILL rule (Lead decision v1, áp dụng per cell = symbol × session × S):**
- `required lift tại x1 > 15.0pp` → **KILL cell**; hoặc
- `unresolved tại session end > 30%` và **không** prereg time-exit với
  b-compression đã tính vào reqW → **KILL cell**; hoặc
- cost **NOT MEASURED** → **BLOCKED**.

| Symbol | Session | Verdict tổng | Cells PASS | Ghi chú |
|---|---|---|---|---|
| **EURUSD** | London | **PASS (S=8)** | S=8 | Primary cell; lift_badj 14.1pp |
| **EURUSD** | NY | **PASS (S=8,10)** | S=8, S=10 | S=10 hợp lệ nhờ time-exit đã prereg + b_obs 1.67 → lift_badj 14.0 |
| **GBPUSD** | London | **PASS (S=8–12)** | S=8,10,12 | lift_badj 10.7–14.5pp |
| **GBPUSD** | NY | **PASS (S=10,12)** | S=10,12 | S=8 KILL sát ngưỡng (15.4 nominal) |
| **USDCHF** | London | **KILL toàn bộ** | — | S=8 nominal 15.4 > 15 + unres 30.4% |
| **USDCHF** | NY | **PASS yếu (S=8)** | S=8 | lift_badj 18.4pp — quá cao, không ưu tiên |
| **USDJPY** | London/NY | **KILL toàn bộ** | — | c_rt 1.4p + baseline WR thấp; mọi cell vượt ngưỡng |
| USDCAD / AUDUSD / NZDUSD | — | **BLOCKED** | — | Chưa có cost đo |
| **XAUUSD** | — | **FAIL (research plane)** | — | c_rt p90 8.03p; mọi S đều vượt ngưỡng lift |

**Kết luận cổng P1 (đã sửa theo lift):** Phase kinh tế đầu tiên **chỉ EURUSD**,
primary **London S=8**. GBPUSD là witness symbol (cùng pass); USDJPY bị loại hẳn
khỏi Phase 1–5 bằng cổng này. XAUUSD giữ nguyên trạng thái FAIL trên research
plane. Điều này trái universe 8 symbol của GOAL — nhưng GOAL cho phép từng sleeve
tự pass theo thời gian (`01. GOAL/GOAL.md:39-51`), và Lead đã chốt XAUUSD loại
khỏi Phase 1–5.

---

## 5. Stress b-compression (điểm chết thật sự)

Bracket 2R chỉ có lời nếu payoff thực giữ gần 2.0R. Số đo §3b cho thấy `b_obs`
**không tự động = 2.0**: tại EURUSD London S=8 b=1.99, nhưng NY S=8 chỉ 1.80 và
NY S=10 chỉ 1.67 — vì các lệnh không phân giải trong session bị time-exit tại
midnight. Hệ quả:

- Chọn S=8/London giữ `b_obs ≈ 2.0` — lý do kỹ thuật chính của quyết định R_S.
- Nếu setup thực thi cho `b_obs < 1.85` tại G3 → **tự động tính lại reqW** và
  ghi verdict theo `reqW(b_obs)`; `< 1.55` → KILL.
- Hệ quả thiết kế bắt buộc: **không manual exit, không scratch, không dời stop
  về BE trong baseline**; time-exit duy nhất được prereg là daily flat
  (server 22:00) + Friday flat, và b-compression của chúng đã nằm trong mô
  phỏng này. Đây cũng là điều T2 P2 đã đóng băng
  (`PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:234-242`).
- Ngược lại, đây là **trục duy nhất repo chưa khai thác**: 45/84 ID tìm entry,
  chỉ 3/84 thay đổi payoff geometry (`20260726_REDTEAM_FULL_REPO_REVIEW.md:228`).

Vì vậy: (a) bracket phải là **stop order + SL/TP broker-side cố định**; (b) mọi
lệnh bị news-flat/Friday-flat cắt ngang phải được log riêng và được stress
như một nhóm làm xấu `b`; (c) không được "diễn giải lại" con số `b_obs`.

---

## 6. Việc còn thiếu (bắt buộc trước economic run)

1. Đo spread/slippage cho **USDCAD, AUDUSD, NZDUSD** bằng
   `02. AlphaFactory/tools/measure_cost_evidence.py` (hoặc sidecar cùng chuẩn)
   rồi build `COST_SOURCE_MANIFEST.json` cho từng symbol — nếu không,
   chúng ở trạng thái BLOCKED.
2. Đo **per-session** spread (London srv 10–12 / NY srv 14–16) cho 4 symbol
   PASS; số hiện tại là all-hours p90 nên conservative.
3. Đo **commission trên deploy venue** (FivePercentOnline-Real) — hiện repo chỉ
   có commission = 0 quan sát trên MQ-Demo + bound $7/lot
   (`20260916_COST_PLANE_AUDIT.md:27-31`); mọi manifest là
   `RESEARCH_PROXY`, `promotion_eligible:false` (`COST_SOURCE_MANIFEST.json:3-9`).
4. Chốt **server-clock offset** (broker +2/+3 vs UTC) bằng bằng chứng tester;
   ATR ở trên tính trên server clock. Session của Volman: UK Open 08:00 UTC,
   US Open 14:30 UTC (bản gốc dùng CET; `volman_upa_excerpt.pdf` p.25-28 bản
   excerpt chính thức).

## 7. Cách tái lập

Script nằm trong package, chỉ **read-only** (đọc parquet cache + in stdout):

```powershell
python "03. EA Developer\EA_VolmanPA\PLAN\probe\atr_probe.py"
python "03. EA Developer\EA_VolmanPA\PLAN\probe\cost_geometry.py"
python "03. EA Developer\EA_VolmanPA\PLAN\probe\cost_table.py"
```

(`atr_probe.py` cần pandas + pyarrow, đã có trên máy này. Bản chạy gốc nằm ở
`%TEMP%\opencode\` trong lúc soạn; bản copy trong `PLAN/probe/` là bản chuẩn để
đưa vào evidence.)

## 8. ASSUMPTION

- `ASSUMPTION:` sidecar spread/slippage MQ-Demo (3–4 ngày tick) đại diện được
  cho phân phối 2016→2026. Nếu broker đổi chính sách spread, p90 phải đo lại.
- `ASSUMPTION:` c_rt p90 (dùng p90 spread + p90 slippage) là biên conservative
  đúng cho research plane; cost thật khi live có thể thấp hơn (deploy plane
  0.9–1.1p cho EURUSD, `20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:16-18`).
- `ASSUMPTION:` commission $7/lot RT áp cho cả XAUUSD theo quy ước 1 pip =
  0.1 USD ≈ $10/lot; nếu broker tính khác, cập nhật manifest.
