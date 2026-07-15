# Owner Brief — Team Refine / Rebuild Session Closeout

Date: 2026-07-14 ~19:30 ICT  
Language: Vietnamese (Owner)  
Evidence docs: English readouts under `03. EA Developer/EA_SonicR/research/readouts/`

## Verdict (ruthless)

**GOAL chưa đạt.** Có đúng **một** child hit research bar dưới tester `current`:
`HYP-SB-MAXKZ2-DENSITY-002` — PF **1.33** / **~2.09**/wk (`20260714_192304`).
Đó **không** phải GOAL: thiếu Real QFSI / cost stress / confirmed suite.

## Team findings (3-critic merge)

| Vai | Kết luận chính |
|---|---|
| Trader | SB thiếu cadence vì kiến trúc session/setup mỏng; Spark không densify ngày được; ITSM cần quality/invalidation không phải densify |
| Quant | ≤6 Model 0 child/campaign; SB micro-short chỉ ~2 trade/5 năm — cấm “săn 2 trade”; cost×1.5 đã giết compose SB+Spark |
| MQL5 | Override-first; ITSM `InpMaxTradesDay` là dead code (1/day thật); Deposit SB phải 100000 |

Merge memo: `readouts/20260714_TEAM_REFINE_REBUILD_3CRITIC_MERGE_MEMO.md`

## Rebuild vs tweak

| Park | Quyết định | Kết quả |
|---|---|---|
| SB weekend-flat A1 | **Không tweak Friday**; densify structural | MaxKZ2 = HIT research; NYPM = cadence↑ PF↓; MaxHold ≈ null |
| Spark Asian | **Không Mon–Thu**; thử symbol transfer | GBPUSD PF 1.07 / 1.66wk — PARK yếu |
| ITSM densifier | **Rebuild session + StrictAlign** | NY PF 1.22 (↑ từ 1.16) vẫn <1.30; London PF 1.12 — PARK |
| H1 LowVol Donchian | Greenfield rebuild | **KILL** PF 0.40 / N=13 |

## Experiment matrix results

| ID | run_id | PF | tpw | N | Disposition |
|---|---|---:|---:|---:|---|
| `HYP-SB-MAXKZ2-DENSITY-002` | `20260714_192304` | **1.33** | **2.09** | 546 | **HIT_RESEARCH_BAR_COST_UNCONFIRMED** |
| `HYP-SB-NYPM-KZ-001` | `20260714_192203` | 1.27 | 2.44 | 635 | PARK (PF regress vs A1) |
| `HYP-SB-MAXHOLD-A2-001` | `20260714_191628` | 1.33 | 1.998 | 521 | PARK (vẫn micro-short) |
| `HYP-ITSM-NYONLY-STRICTALIGN-002` | `20260714_191955` | 1.22 | 2.07 | 540 | PARK |
| `HYP-ITSM-LONDON-ONLY-STRICTALIGN-002` | `20260714_192116` | 1.12 | 1.85 | 482 | PARK |
| `HYP-SPARK-ASIAN-GBPUSD-001` | `20260714_191507` | 1.07 | 1.66 | 432 | PARK yếu |
| `HYP-H1-LOWVOL-DONCHIAN-MR-001` | `20260714_191727` | 0.40 | ~0.05 | 13 | **KILL** |

Baseline control SB A1: `20260714_002505` PF~1.34 / ~1.99/wk.

## Distance to GOAL

| Chiều | Best hiện tại | GOAL | Gap |
|---|---|---|---|
| PF after verified cost | **unknown** (tester only) | >1.30 verified | **Real QFSI bắt buộc** |
| Cadence | MaxKZ2 **~2.09**/wk | 2–5 | research OK trên Demo |
| Joint research (tester) | MaxKZ2 clears | — | closest single-sleeve tonight |
| Confirmed / promotion | none | full suite | blocked |

## Next autonomous moves

1. **Owner-physical (highest EV):** login `FivePercentOnline-Real` + QFSI → reprice MaxKZ2 `192304` (và A1 `002505`).
2. Agent: **stop** thêm densify SB / session spam ITSM tối nay (family stop sau 2 miss + 1 hit).
3. Child tiếp theo chỉ khi có thesis structural mới (invalidation rebuild ITSM / Spark mechanism mới) — không mine hour/day từ readout.
4. Portfolio SB+Spark vẫn Phase-0 blocked — không code compose EA từ PF list.
5. Integrity giữ nguyên: child ID + frozen prereg trước readout; closed-bar; missing cost ≠ 0.

## Artifacts

- Merge: `readouts/20260714_TEAM_REFINE_REBUILD_3CRITIC_MERGE_MEMO.md`
- Matrix: `readouts/20260714_TEAM_REFINE_REBUILD_OPTION_MATRIX_V1.md`
- Coordinator: `readouts/20260714_STRATEGY_REBUILD_CAMPAIGN_COORDINATOR.md`
- Receipts: `preflight/rebuild_campaign/`
- `hot.md` Active Truth updated this closeout
