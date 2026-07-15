# BLOCKED_NO_LEGAL_THESIS + Matched-Control Blocker — 2026-07-14

Status: `BLOCKED_NO_LEGAL_THESIS` / `MATCHED_CONTROL_NOT_AUTHORIZED` / `NO_NEW_MODEL0`  
Authority: Owner free-MT autonomy toward GOAL; GPT waived; `hot.md`; shelf inventory.  
Agent: Grok 4.5 High Fast (continuation after LondonORB park / Keltner kill).

## Task checklist

| # | Instruction | Result |
|---|---|---|
| 1 | Model 0 `HYP-SB-WEEKEND-FLAT-001` / weekend-flat A1 if not yet done | **SKIP — already complete** |
| 2 | One new independent price thesis outside kill/park twin list | **`BLOCKED_NO_LEGAL_THESIS`** |
| 3 | Compile + Model 0 + readout + hot.md for that thesis | **N/A** (no legal ID) |
| 4 | Park shelf of best near-misses; no GOAL claim | **Maintained** (below) |
| Fallback | Matched control Model 0 for best parked PF≥1.25 sleeve | **BLOCKED by prereg** |

## 1) SB weekend-flat — already Model 0'd (no re-run)

Authoritative pair under research freeze
`preregs/20260713_H_SB_WEEKEND_FLAT_001_RESEARCH_FREEZE.md`:

| Role | run_id | Overrides | PF | Trades | ~tpw | Net |
|---|---|---|---:|---:|---:|---:|
| Control | `20260714_002046` | `InpUseWeekendFlat=0` | 1.33 | 519 | ~1.99 | +7600.35 |
| Challenger A1 | `20260714_002505` | `InpUseWeekendFlat=1;InpFridayFlatHour=21;InpFridayFlatMinute=45` | 1.34 | 520 | ~1.99 | +7875.93 |

USDJPY M15 2021-2025 Deposit=100000. Tester `current` / Demo research-proxy only — **not confirmed**. Readout: `readouts/20260714_HYP_SB_WEEKEND_FLAT_001_MODEL0_READOUT.md`.

## 2) New independent thesis — `BLOCKED_NO_LEGAL_THESIS`

Surfaces rechecked against
`readouts/20260714_BLOCKED_NO_LEGAL_THESIS_SURFACE_INVENTORY.md`,
`readouts/20260714_PRICE_M15_DUAL_FILTER_SHELF_EMPTY_SCAN.md`,
`readouts/20260714_AUTONOMOUS_GOAL_HYPOTHESIS_BACKLOG_V1.md`, and
`STRATEGY_LOG.md`:

| Candidate class | Why not legal now |
|---|---|
| Price-M15 dual-filter shelf | EMPTY for new agent-executable IDs |
| LondonORB / Keltner | Just executed this campaign (park / kill) — not new |
| LondonORB rescue, Keltner twin, Spark densify, ITSM T10 | Explicitly banned |
| H1 InsideBar S232 / multi-pair IB | Twin of killed `HYP-INSIDEBAR-M15-001` GOAL transfer |
| H1OpenBreak / OpeningMomentum / HOLO / Engulfing-Pin | Already failed or killed as HourOpen family |
| Carry / COT / bond / OIS / equity-bond / VIX / USBILL | Offline or Model 0 kills |
| SOFR−SONIA / HY-MOVE / DEXUSEU / monthly carry | Inventory-rejected twins |
| Phase 0 portfolio compose / USD-factor | Contract / Real-QFSI blocked |

**Verdict:** no new independent price thesis cleared for probe → registry → prereg → Model 0. Do not mint cosmetic IDs.

## 3) Fallback matched control — `MATCHED_CONTROL_NOT_AUTHORIZED`

Requested control form: **disabled signal / random hour block disabled**, on best parked sleeve with **PF≥1.25**.

### Best PF≥1.25 parked sleeves

| Sleeve | Authoritative run | PF | ~tpw | Eligible by PF? |
|---|---|---:|---:|---|
| SB A1 weekend-flat | `20260714_002505` | **1.34** | **~1.99** | Yes (best) |
| Spark Asian | `20260714_002821` | **1.31** | **~1.25** | Yes (cadence short) |
| ITSM | `20260714_003920` | 1.16 | ~3.27 | No (PF&lt;1.25) |
| LondonORB | `20260714_005126` | 1.17 | ~1.58 | No (PF&lt;1.25) |

### Prereg gate (fail-closed)

| Sleeve | What prereg/freeze allows | Disabled-signal / random-hour control? |
|---|---|---|
| **SB** | Only A1 weekend-flat matched pair: `InpUseWeekendFlat=0` vs `=1` (already run) | **Not authorized.** No frozen `InpEnabled=0`, placebo/random-KZ, or hour-shift control contract. Draft Phase 0 prereg still `UNSET` for broader matched-control design and forbids completing placeholders after outcomes. |
| **Spark** | Single-arm Model 0 screen only (`20260714_H_SPARK_ASIAN_M15_001_PREREG.md`); kill/park gates; bans day/hour mining after readout | **Not authorized.** No control/challenger design; `InpKillSwitch` / `InpUseTrendFilter` ablations were not frozen as matched control. |

Opening a post-park “disabled signal” or “random hour” Model 0 from the parked readout would be **post-hoc ceremony**, not a frozen test plan.

**Blocker code:** `MATCHED_CONTROL_PREREG_GAP_DISABLED_SIGNAL_OR_RANDOM_HOUR`

**No new run_id** from this fallback.

## 4) Park shelf (honest; GOAL unmet)

| Rank | ID | run_id | PF | ~tpw | Note |
|---|---|---|---:|---:|---|
| 1 | `HYP-SB-WEEKEND-FLAT-001` | `20260714_002505` (ctrl `20260714_002046`) | 1.34 | ~1.99 | Nearest dual-gate book; Real QFSI required |
| 2 | `HYP-SPARK-ASIAN-M15-001` | `20260714_002821` | 1.31 | ~1.25 | Cadence short of GOAL 2.0 |
| 3 | `HYP-ITSM-PULLBACK-M15-001` | `20260714_003920` | 1.16 | ~3.27 | Cadence OK; PF below research bar |
| 4 | `HYP-LONDON-ORB-M15-001` | `20260714_005126` | 1.17 | ~1.58 | Parked tonight; not PRIORITY_NEAR_GOAL |

Compose Spark+ITSM offline pooled PF 1.175 FAIL — do not code portfolio EA from that pair.

## Ship run_ids (this pass)

- **New Model 0 this pass:** none (`BLOCKED_NO_LEGAL_THESIS` + matched-control prereg gap).
- **Cited prior (SB already done):** `20260714_002046`, `20260714_002505`.
- **Cited park shelf:** `20260714_002821` (Spark), `20260714_003920` (ITSM), `20260714_005126` (LondonORB).

## Next Owner-physical / agent-legal moves

1. **Highest GOAL leverage:** login `FivePercentOnline-Real` + read-only QFSI for parked SB A1 (then Spark).
2. Agent: only reopen Model 0 after a **new** independent thesis with written de-dup + probe survivor + frozen prereg — or after an Owner-approved **a priori** matched-control child prereg for SB/Spark that explicitly freezes disabled-signal or placebo-hour design **before** any run.
3. No ChatGPT Deep Research. No kill-list rescue.
