# Coordinator — Deal-history cost unblock + post-cost Model 0 rebuild

Date: 2026-07-14 ~23:20 ICT  
Process: no GPT; no densify MaxKZ2; no invent zero costs; no-Git  
Status: **`PARTIAL`** = `COST_IMPORT_READY` + `BLOCKED_NEEDS_OWNER_DEAL_EXPORT` + `MODEL0_READY_TERMINAL_BLOCKED`

## Verdict

Cost path is **import-ready** but still **data-starved**. Live Real history
re-import confirms only **11** deals (EURUSD commission N=2, USDJPY=0).
Owner must drop Account History exports to raise commission samples.
Slippage still cannot be minted by passive capture.

Model 0 structural wave is **frozen + compiled (OutsideRev) + receipt-bound**
but **not executed**: `alpha.ps1` fail-closes on Owner Real `terminal64`
(PID observed **29076** at attempt). Agent did not kill Real.

## A) Owner deal-export checklist (copy/do)

1. Keep login on **`FivePercentOnline-Real`**.
2. MT5 Toolbox → **History** → right-click → **All History** (or ≥90d of closed deals).
3. Right-click → **Report / Save as Report** → save `Deals.htm` (and CSV if available).
4. Optional: broker commission schedule PDF/CSV for reference only.
5. Drop files into:
   `02. AlphaFactory/evidence/execution/FivePercentOnline-Real/owner_deal_export_drop/`
   (see `README.md` there for required columns).
6. Tell agent to run:
   ```text
   python "02. AlphaFactory/tools/import_owner_deal_history_qfsi.py" --from-drop "<drop folder>" --out-dir "02. AlphaFactory/evidence/execution/FivePercentOnline-Real/20260714_DEAL_HISTORY_IMPORT"
   ```

### What clears which gate

| Artifact | Clears | Does not clear |
|---|---|---|
| Account History Deal export with Commission + Position ID | commission lifecycles toward ≥30/symbol | slippage |
| Side-referenced broker exec report / logged pre-send quotes | slippage ≥100/symbol | — |
| Passiveive quote capture alone | quote days / spread | commission, slippage |

**Missing slippage ≠ 0.** Do not invent zeros.

### Agent import already done (live)

| Item | Result |
|---|---|
| Tool | `02. AlphaFactory/tools/import_owner_deal_history_qfsi.py` |
| Live import | `…/20260714_DEAL_HISTORY_IMPORT/` |
| Manifest SHA | `00DAC2A7188D7A090EAB7D4D647F6055D08BCEC0D9CB54ADDCCFDC61935057D4` |
| Raw deals | **11** |
| Commission N | EURUSD **2** / USDJPY **0** / GBPUSD **0** / XAUUSD **0** / BTCUSD **3** |
| Owner drop files | **0** |
| Eligible verified-cost bundles | **0** |
| Receipt | `preflight/20260714_DEAL_HISTORY_COST_UNBLOCK_RECEIPT.json` SHA `FDAB15472514BCF6111AF15564EED18EBA8B66BD7129497E8B5CA27296C794BB` |

## B) Model 0 matrix (post-MaxKZ2 Real-P50 FAIL)

De-dup: `readouts/20260714_POST_COST_REBUILD_DEDUP_CLEARANCE.md`

| # | hypothesis_id | Thesis | EA | Receipt SHA | Run | Verdict |
|---|---|---|---|---|---|---|
| 1 | `HYP-H4-OUTSIDE-REV-001` | H4 outside+WR7 failed-expansion fade; RR=3 | `EA_H4OutsideRev` (compiled 22768 B) | `489BAA58…EC89` | **null** | `BLOCKED_UNRELATED_TERMINAL64` |
| 2 | `HYP-ITSM-NYONLY-RR3-THICK-001` | NY-only StrictAlign + RR3 thick | `EA_ITSM` | `63C18408…31EB` | **null** | `BLOCKED_UNRELATED_TERMINAL64` |
| 3 | `HYP-SB-MAXKZ2-PARTIAL-R1-001` | MaxKZ2+A1 + PartialClose 50%@1R | `EA_SilverBullet` | `EC938032…1CA8` | **null** | `BLOCKED_UNRELATED_TERMINAL64` |

Blocker code: `UNRELATED_TERMINAL64_OWNER_REAL_LOGIN_FAIL_CLOSED`  
Logs: `preflight/20260714_POSTCOST_*_BT.log`

### Owner action for Model 0 (1 line)

**Đóng tạm terminal Real (hoặc cho exclusive tester), rồi bảo agent chạy lại 3 Model 0 trên — alpha.ps1 chưa portable song song; agent không kill Real.**

### Explicit bans honored

No MaxKZ2 densify; no ChatGPT; no GOAL/confirmed claim; tester cost caveat only;
partial Real ~$2.31 P50 remains caveated (RR2 PASS / MaxKZ2 FAIL unchanged).

## vs GOAL

| Dimension | State |
|---|---|
| PF>1.30 after **verified** cost | **Blocked** (eligible bundles=0) |
| Cadence 2–5/wk | Research-proxy only on prior RR2 |
| Cost stress x1.5/x2 verified | Open |
| Confirmed / portfolio-sleeve | Not claimed |

## Next legal moves

1. Owner deal export → re-import → re-inventory QFSI.
2. Owner close Real temporarily → execute the three frozen Model 0s → kill/park fast.
3. Do **not** densify MaxKZ2 while waiting.
