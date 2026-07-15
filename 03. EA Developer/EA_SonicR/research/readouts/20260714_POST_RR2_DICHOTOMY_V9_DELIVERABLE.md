# Deliverable — Post RR2 FAIL → Dichotomy + V9 + data-surface/QFSI hygiene

Date: 2026-07-14 ~23:55 ICT  
Lane: Owner path tiếp — data-surface / QFSI (không densify structural)  
GPT: waived · Owner MT kill/open-auth ON (no in-flight tester)

## 1) Board structural (đã đóng — không densify)

### Prior
| Run / ID | Gate |
|---|---|
| RR2 Model0 `20260714_231750` | PF **1.156** / ~1.99 tpw → **PARK_MISS**; Real P50 FAIL |
| Historical shelf `194548` | PF 1.378 — disk only; not current tester truth |

### Dichotomy + V9
3/3 dichotomy KILL · 3/3 V9 KILL · **zero Model 0**.  
Receipts: dichotomy `7B0D6075…798D90` · V9 `3F47416C…03CBC8`.

## 2) QFSI progress (Real)

| Item | Status |
|---|---|
| `terminal64` / Real | Live MT5 probe: server=`FivePercentOnline-Real` ok=`True` |
| Capture `005_POSTAUTH` | LIVE — quotes accumulating |
| Captures 001–004_EXTENSION | COMPLETE_PARTIAL on disk |
| Full QFSI | **`STOP_DATA_FRONTIER`** — quote_distinct_utc_dates=1 << 90; commission_unique_EURUSD=2 << 30 (USDJPY=0); slippage_fills=0 MISSING≠0 |
| Commission unique | EURUSD N=**2** @ $4/lot RT; USDJPY **0** |
| Slippage fills | **0** (MISSING≠0 — không pretend 0) |
| Owner deal-export drop | new files = **0** |
| Live deal-history import | `20260714_DEAL_HISTORY_IMPORT_LIVE` — raw deals **11**; EURUSD commission **2** (same clue); USDJPY **0**; BTCUSD **3** (out-of-scope); slip **0** MISSING |

Không kill capture đang chạy. Không đặt lệnh live.

## 3) Broker spread / cost table

Path: `preflight/20260714_BROKER_SPREAD_COST_TABLE_QFSI.json`  
SHA: `A0DD6BDBFDC311720CF963E5D05D9D5BBD7C9E42F9A99E1EAE68787334AA2964`

Canonical USDJPY (lot P50=0.5):  
- trade cost P50 ≈ **$2.6168**  
- trade cost P90 ≈ **$2.9251**  
Formula: `(spread_usd/lot + EURUSD commission clue) * lot_p50`; slippage **không** cộng vì MISSING.

Label: **`PARTIAL_BROKER_TABLE_PROXY`** — session-hour coverage sparse (capture windows ngắn); chưa đủ 90 ngày quote.

## 4) Diagnostic reprice (không rescue)

| Book | Base PF | Table P50 ×1 | ×1.5 | ×2 |
|---|---:|---:|---:|---:|
| Shelf `194548` | 1.378321 | 1.315991 | 1.286178 | 1.257214 |
| Fresh `231750` | 1.156039 | 1.105257 | 1.080902 | 1.057199 |

Đọc: shelf `194548` vẫn dày hơn dưới cùng cost table; `231750` vẫn **PARK_MISS** / không HIT. Không densify RR/MaxKZ.

## 5) COT join mới (≠ |z|) — offline only

Hypothesis: `HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001`  
Rule a priori: allow iff `|net_lev| ≤ median(|net| prior 52w)` — anti-crowd size-budget, **không** retune z.

| | N | PF | tpw | x1.5 |
|---|---:|---:|---:|---:|
| Size-budget | 117 | 1.6356 | 0.4495 | 1.2233 |

Verdict: **KILLED_AT_OFFLINE_PROBE** · notes=['cadence_fail'] · Model0 withheld.

Sibling (parallel lane): same hyp-id scale-PnL size-budget variant cũng **KILL** (`stress_fail`, N=524) — `readouts/20260714_COT_SIZEBUDGET_RR2_PROBE.md`. Không retune threshold.

## 6) vs GOAL

GOAL **unmet**. `COST_PROVENANCE_GAP` = **NARROWED_NOT_CLEARED** (table hẹp gap spread; slip/commission/90d vẫn mở). Best research shelf vẫn `194548` dưới partial Real cost; confirmed/GOAL cần full QFSI hoặc Owner-accepted verified-cost contract.

## 7) Next

1. Giữ Real + để `005` chạy hết; nếu cần → launch capture dài hơn / Owner drop deal-history (commission≥30/symbol + slip fills).  
2. Không densify structural kill-list.  
3. Surface tiếp theo: Owner-sourced non-price khác, hoặc chờ frontier QFSI nhích — không shotgun price-twin.  
4. Phase-0 vẫn BLOCKED.

## hot.md

Cập nhật Active Truth + Next Move + `COST_PROVENANCE` status trong cùng turn.

Receipt: `preflight/20260714_QFSI_DATA_SURFACE_HYGIENE_RECEIPT.json` SHA `9E4B78B7B162195AB217235EE9088B9331F0B715151323CF3905A3C3D6353E25`
