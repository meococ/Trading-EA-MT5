# Deliverable — Structural MULTISYM (offline-first, escape USDJPY)

Date: 2026-07-14 ~23:55 ICT  
Language: tiếng Việt (Owner) / evidence EN  
GPT: waived · Escape USDJPY TF · No MaxKZ/RR densify · No Phase-0 wait

## 1) Việc đã chạy

Sau V5 (USDJPY 5/5 KILL) + V6 (impulse/halfback KILL), Owner yêu cầu **thoát
bão hòa USDJPY TF** → 6 thesis structural mới trên EURUSD / GBPUSD / XAUUSD
(Phase-0 draft scope), de-dup cứng, probe offline 2021–2025.

**Hygiene stem:** lần ghi đầu đè V6 → tạm gắn V7 → peer đã chiếm V7
(coil/retest/dayfade) → board này dùng stem collision-safe
`STRUCTURAL_MULTISYM_*`. V6 gốc restore pointer từ registry.

| ID | Symbol | N | PF | tpw | cost×1.5 | Verdict |
|---|---|---:|---:|---:|---:|---|
| London-overlap range break | EURUSD | 725 | 1.069 | 2.78 | 0.986 | **KILL** |
| NY-open impulse hold | GBPUSD | 46 | 0.740 | 0.18 | 0.681 | **KILL** |
| Asia-compress → London break | XAUUSD | 0 | — | — | — | **KILL** (object rỗng) |
| D1 outside → H1 fade | EURUSD | 74 | 0.695 | 0.28 | 0.608 | **KILL** |
| H4 break → H1 open PB | GBPUSD | 774 | 0.953 | 2.97 | 0.895 | **KILL** |
| H4 wick-reject fade | XAUUSD | 1059 | 0.877 | 4.06 | 0.764 | **KILL** |

Cost proxy: FX +$12 / XAU +$25.  
Receipt SHA: `C802A33A2601D65AF953814EBB02CDFE7E82840A86E4666839FA1346A1C514D3`  
JSON: `preflight/20260714_STRUCTURAL_MULTISYM_OFFLINE_PROBES.json`  
De-dup: `readouts/20260714_STRUCTURAL_MULTISYM_DEDUP_CLEARANCE.md`  
Closeout: `readouts/20260714_STRUCTURAL_MULTISYM_SESSION_CLOSEOUT.md`

Peer V7 coil (không đụng board này): 3/3 KILL —
`STRUCTURAL_V7_COIL_RETEST_DAYFADE_*`.

## 2) vs GOAL

**0/6** offline survivor → **0 Model 0**.  
Near-miss EUR overlap (PF 1.069 / stress 0.986) **không** đủ gate — cấm
densify giờ/RR.  
Best shelf: RR2 `194548` PF **1.378** / ~**2.01**/wk (research HIT; GOAL +$12 FAIL).

## 3) Park / kill / survive

- MULTISYM: **KILL all** — không densify.
- Không chờ Phase-0 cho discovery.
- Không spam Model 0 trên sách kill.
- Không retune V1–V6 / peer V7 coil / MaxKZ / RR2.

## 4) Next moves

1. Object **mới** ngoài V1–V7 + MULTISYM (ưu tiên class khác: exogenous /
   microstructure không trùng session-break/fade/coil đã kill).
2. QFSI = hygiene song song nếu promote sau này.
3. MT5 free cho Model 0 **chỉ khi** có `PROBE_SURVIVOR` + registry/prereg.
