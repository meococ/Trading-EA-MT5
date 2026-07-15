# Deliverable — CONTINUE clear MT → Model 0 IB/GBPJPY + ATR (VN parent)

Date: 2026-07-14 ~23:40 ICT  
Authority: Owner CONTINUE (Clear MT contention → Model 0 IB then GBPJPY; prep ATR)  
GPT: waived · Grok · no-Git · cost honesty

## Verdict

**Hàng đợi CONTINUE đã đóng.** Real blocking đã được dừng; Model 0 IB +
GBPJPY + ATR%ile đều đã có evidence trên disk — **không research HIT**.
GOAL vẫn unmet. Shelf tốt nhất: RR2 `194548`.

## Infra (agent làm trong session này)

| Bước | Kết quả |
|---|---|
| Quan sát blocker | `terminal64` PID **27628** — Real `FivePercentOnline-Real` / login **26451822** (theo residual receipt trước đó; **không** đọc lại password) |
| Hành động | `Stop-Process -Force` PID **27628** — chỉ process tester-contention; **không** xóa account/credential |
| Sau stop | `Get-Process terminal64` = **0** (CLEAR) |
| Receipt | `preflight/20260714_CONTINUE_CLEAR_REAL_PID27628_RECEIPT.json` SHA `61DACD5A…937F2C` |

Ghi chú: terminal có thể tự mở lại sau đó; các Model 0 Wave4/Wave5 đã chạy
trong cửa sổ exclusive sau khi CLEAR (race song song với lane khác).

## Board Model 0 (xác minh cost_stress / readout)

Screen HIT: PF>1.30 ∧ tpw∈[2,5] ∧ x1.5≥1.25 ∧ x2≥1.00 — **không ID nào đạt**.

| ID | Run | PF | N | tpw | +$12 x1.5 / x2 | Verdict |
|---|---|---:|---:|---:|---|---|
| `HYP-M15-IB-OVERLAP-BREAK-001` | `20260714_223618` | **1.05** | 987 | **~3.79** | **0.89 / 0.84 FAIL** | **PARK** weak |
| `HYP-GBPJPY-LEAD-USDJPY-H1-001` | `20260714_223748` | **1.10** | 1337 | **~5.13** | **0.92 / 0.87 FAIL** | **PARK** weak |
| `HYP-H1-ATR-PCTILE-BREAK-001` | auth `20260714_224917` (twin `225208`) | **1.10** | 445 | **~1.71** | **~0.94 / ~0.89 FAIL** | **PARK** weak |

ATR đã qua de-dup Wave5 (`readouts/20260714_DISCOVERY_WAVE5_DEDUP_CLEARANCE.md`)
trước code — không densify ATR%ile / Donchian / RR.

Closeout EN: `readouts/20260714_DISCOVERY_WAVE4_IB_RV_GBPJPY_CLOSEOUT.md`,
`readouts/20260714_DISCOVERY_WAVE5_ATR_ASIA_NYIB_CLOSEOUT.md`.

## Integrity / ceremony

- Alpha finalize vẫn có bug `required_sidecars: [null]` sau report ready;
  metrics lấy từ report + `sonic_cost_stress` (đã có sẵn trong
  `analysis/cost_stress_base12.json`).
- Cost grade: `UNVERIFIED_TESTER_DEFAULT` — không phải Real QFSI / không GOAL.
- Optional SBSparkBook: đã Model 0 riêng `20260714_224302` **KILL** PF 1.219 —
  không reopen trong CONTINUE này.
- Cấm densify: IB hours / GBPJPY lead thresh / ATR%ile bands / MaxKZ/RR /
  EQHL/PIN/ThreeBar/Outside/Engulf.

## vs GOAL

Chưa đạt. RR2 `194548` vẫn gần nhất (PF 1.378 / ~2.01/wk; +$12 x1.5 FAIL).
Bài học Wave4/5: sleeve cadence ≠ sleeve dày expectancy — không ghép hậu nghiệm.

## Next (không phụ thuộc login Real)

1. Structural rebuild / failure-packet Deep Research cho edge **joint** mới —
   không spam session/vol gate đã PARK/KILL.
2. Phase-0 RR2+Spark compose chỉ khi contamination clear (universe đã freeze).
3. Real/QFSI song song hygiene only — không headline R&D stop.
