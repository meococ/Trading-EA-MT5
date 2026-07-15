# Deliverable — MaxKZ2 QFSI / Real cost path FAIL-CLOSED

Date: 2026-07-14 (refresh)  
Process: no GPT; Real login + aggregated capture reprice  
Language: tiếng Việt (Owner) / evidence EN

## 1) MT5 server

| Field | Value |
|---|---|
| Observed | `FivePercentOnline-Real` |
| Login | `26451822` |
| Match expected Real | **YES** |
| Probe SHA | `7C38E9DC2166FBAF269ABFB3E34AF30032EE04A3FC0A7CEF7BD1F3FCF3CDF6A3` |

## 2) QFSI capture

| Field | Value |
|---|---|
| Inventory verdict | `STOP_DATA_FRONTIER` |
| Eligible bundles | **0** |
| Full QFSI | **FAIL** (`STOP_DATA_FRONTIER`) |
| Slippage | MISSING ≠ 0 |
| USDJPY commission rows | 0 |
| EURUSD commission clue N | 12 |

Capture totals (quotes):  
- `20260714_QFSI_REAL_001`: quotes=1313, comm=4, slip=0
- `20260714_QFSI_REAL_002`: quotes=421, comm=2, slip=0
- `20260714_QFSI_REAL_003_CONTINUATION`: quotes=3376, comm=2, slip=0
- `20260714_QFSI_REAL_004_CONTINUATION`: quotes=2267, comm=2, slip=0
- `20260714_QFSI_REAL_004_EXTENSION`: quotes=4623, comm=2, slip=0

## 3) Cost model (USDJPY)

| Input | Value |
|---|---|
| Spread source | `AGGREGATED_CAPTURE_QUOTE_TICKS` |
| Spread USD/lot P50 / P90 | 1.235163 / 1.852744 |
| Commission RT/lot | $4.00 (EURUSD_N12_CLUE_TRANSFERRED_TO_USDJPY) |
| Lot P50 | 0.5 |
| Base $/trade P50 / P90 | **2.6176** / **2.9264** |

## 4) MaxKZ2 vs GOAL after Real cost

Auth run `20260714_192304` (tester PF 1.33 / ~2.09/wk). Twin `192515` protocol check: YES.

| Book | Scenario | x1 PF | x1.5 PF | x2 PF | GOAL cost-stress |
|---|---|---:|---:|---:|---|
| MaxKZ2 `192304` | Real P50 | 1.267 | 1.235 | 1.204 | **FAIL** |
| MaxKZ2 `192304` | Real P90 | 1.259 | 1.224 | 1.189 | **FAIL** |
| Twin `192515` | Real P50 | 1.267 | 1.235 | 1.204 | FAIL/n/a |
| RR2 `194221` (control) | Real P50 | 1.316 | 1.286 | 1.257 | PASS |

**Quyết định MaxKZ2:** `PARK_FAIL_REAL_PARTIAL_COST_STRESS` — **PARK**. Không densify. Không chạy confirmed/stress/holdout ceremony (fail-closed trước gate).

Cadence vẫn ~2.09/wk (không đổi bởi haircut báo cáo); PF sau Real cost **dưới** GOAL 1.30 @x1.

## 5) Compose MaxKZ2 + Spark (a priori 1:1)

| Metric | Value |
|---|---:|
| Spark run | 20260714_002614 (EA_M15SparkAsian) |
| Weight rule | EQUAL_JOIN_1_1_A_PRIORI |
| Pooled N / tpw | 871 / 3.34 |
| PF x1 / x1.5 / x2 | 1.239 / 1.196 / 1.154 |
| Cadence 2-5 | PASS |
| Cost-stress-like | FAIL |

Promote: **NO** (PARENT_MAXKZ2_REAL_COST_STRESS_FAIL). Khong post-hoc weight mining.
JSON: preflight/20260714_OFFLINE_MAXKZ2_SPARK_REAL_P50_COMPOSE.json

## 6) Next moves

1. Giữ MaxKZ2 **PARK** dưới Real partial cost; full QFSI vẫn tích lũy (004_EXTENSION / ≥90d).
2. Không densify MaxKZ/RR; không mine giờ/ngày.
3. RR2 vẫn là sleeve partial-Real cost-stress PASS — Model 0 rebind / confirmed gates chỉ khi Owner giải phóng terminal Exclusive tester + verified cost đủ doctrine.
4. Discovery độc lập tiếp: stub `HYP-H4-OUTSIDE-REV-001` (prereg trước code) nếu Owner muốn shelf mới.
5. `COST_PROVENANCE_GAP` = **NARROWED_NOT_CLEARED**.

## Receipt

`preflight/20260714_MAXKZ2_QFSI_REAL_FAILCLOSED_RECEIPT.json`  
SHA256: `3D1DBBF406AE54788AB04906494721E841FCE83D5393F410B5C73DAF502F8E67`
