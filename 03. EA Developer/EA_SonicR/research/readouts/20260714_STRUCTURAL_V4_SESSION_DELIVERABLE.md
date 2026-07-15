# Deliverable — Structural rebuild V4 (offline-first)

Date: 2026-07-14 ~23:25 ICT  
Language: tiếng Việt (Owner) / evidence EN  
GPT: waived · No MaxKZ/RR densify · No Wave3–5 / V1–V3 retune · No Phase-0 wait

## 1) Việc đã chạy

Shelf next-object trống sau V3 → thiết kế **5 thesis structural mới** (trader +
quant + MQL5), de-dup cứng, probe offline closed-bar trên USDJPY 2021–2025
(MT5 Real rates, read-only).

| ID | Định nghĩa (a priori) | N | PF | tpw | +$12 x1.5 | Verdict |
|---|---|---:|---:|---:|---:|---|
| `HYP-H1-ORDERBLOCK-MITIGATION-001` | Displace → OB body → mitigation hold | 412 | 0.985 | 1.58 | 0.931 | **KILL** |
| `HYP-D1-INSIDE-H4-BREAK-001` | D1 inside → H4 break+accept | 369 | 0.987 | 1.41 | 0.900 | **KILL** |
| `HYP-H1-LONDON-DRIVE-FAIL-FADE-001` | London open displace fail → fade | 298 | 0.915 | 1.14 | 0.852 | **KILL** |
| `HYP-M15-ASIA-BREAK-FAIL-FADE-001` | Asia break fail-back → fade mid | 102 | 0.923 | 0.39 | 0.871 | **KILL** |
| `HYP-H4-BREAK-PAUSE-BREAK-001` | Break → pause inside → resume | 31 | 0.635 | 0.12 | 0.589 | **KILL** |

Receipt SHA: `754EF77EDA5CA13EC71167D83F327753D802BC4617BA524EC4B20A6277A57F3F`  
JSON: `preflight/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V4.json`  
De-dup: `readouts/20260714_STRUCTURAL_V4_DEDUP_CLEARANCE.md`  
Board MD: `readouts/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V4.md`

## 2) vs GOAL

GOAL = PF>1.30 ∧ 2–5/wk ∧ cost-stress. **0/5** clear offline survivor →
**0 Model 0** (đúng doctrine kill-fast).

Best shelf giữ: RR2 `20260714_194548` PF **1.378** / ~**2.01**/wk (research HIT;
GOAL +$12 FAIL / PARK).

## 3) Park / kill / survive

- V4: **KILL all** — không densify OB%/Asia hours/London open/break-pause.
- Không chờ Phase-0 Owner clear (discovery không phụ thuộc compose).
- Không spam Model 0 trên sách kill.

## 4) Next moves

1. Tiếp offline object **mới** ngoài V1–V4 / Wave3–5 (hoặc đổi symbol-class
   structural nếu de-dup USDJPY M15/H1/H4 đã bão hòa).
2. QFSI / Real cost = hygiene song song — không headline.
3. Phase-0 RR2+Spark chỉ khi Owner chủ động clear contamination — không stall.
