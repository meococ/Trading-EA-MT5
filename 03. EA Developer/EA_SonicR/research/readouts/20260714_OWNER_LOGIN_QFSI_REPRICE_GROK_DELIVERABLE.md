# Deliverable — Owner "đã login" → Real verify + QFSI/reprice (Grok)

Date: 2026-07-14 ~22:10 ICT  
Process: no GPT; nested `cursor-grok-4.5-high-fast`; no-Git  
Language: tiếng Việt (Owner) / evidence EN

## 1) Real login verified?

| Field | Value |
|---|---|
| Expected server | `FivePercentOnline-Real` |
| Observed server | `FivePercentOnline-Real` |
| `server_match` | **true** |
| Probe | `TARGET_SERVER_READONLY_PROBE_COMPLETE` |
| Probe file | `preflight/v4_data/20260714_MT5_READONLY_PROBE_V6_OWNER_LOGIN.json` |
| Probe SHA256 | `A35173ED7F6B3A296A61985C023733B1AE8C8E2CF4C879F9BEECAB2DAD03B93B` |
| Account fingerprint | `09DB5E9C091F23DF9E024E684BBA994D00CBD84CDEF2CFBA0C5D064EACCB32AB` |
| Server fingerprint | `CE114ABFB8C653A060DAD7EA33FAF948B5786F691953B2D4E230EB7986120797` |
| terminal64 | PID **6596** (started ~22:01 ICT) |
| `trade_allowed` (probe V6) | false |
| Not Demo | **YES** — not `MetaQuotes-Demo` |

## 2) QFSI artifact paths

| Artifact | Path / note |
|---|---|
| Live capture RUNNING | `02. AlphaFactory/evidence/execution/FivePercentOnline-Real/20260714_QFSI_REAL_004_EXTENSION/` (PID **46404**, duration 7200s) |
| Prior captures | `…/20260714_QFSI_REAL_001` … `_004_CONTINUATION` |
| Deal history re-import | `…/20260714_DEAL_HISTORY_IMPORT_V2/` (manifest SHA `E08855CFCADBA96496375D5B6510563FCAD9DF6C76C5EFE6AFBD3C710CC6A5AC`) |
| Inventory V6 | `preflight/v4_data/20260714_EXECUTION_DATA_INVENTORY_V6.json` SHA `A47E82E41E3EC40FF3CC91E811327EBD8E045907F7431A055ADED78790DB04A1` |
| Inventory verdict | **`STOP_DATA_FRONTIER`** / eligible bundles **0** |
| Commission (live history) | EURUSD=**2**, GBPUSD=0, XAUUSD=0, **USDJPY=0**, BTCUSD=3 |
| Slippage | **0 rows** = MISSING ≠ 0 |
| Quote elapsed days | ≪90 |

Full QFSI verified-cost path: **still FAIL** (cannot invent commission/slippage samples).

## 3) Cost models used (honest labels)

| Model | Base $/trade @ lot 0.5 | Source | Label |
|---|---:|---|---|
| Live-tick P50 (this session) | **~$2.3088** | USDJPY live ticks + EURUSD commission clue N=2 | `REAL_LIVE_SPREAD_PLUS_EURUSD_COMMISSION_CLUE` |
| Aggregated-capture P50 (parallel fail-closed) | **~$2.6176** | Aggregated capture spreads + transferred commission | more conservative sibling |

Slippage never treated as zero. Neither model is full QFSI / confirmed.

## 4) Metrics after Real cost vs GOAL

GOAL: PF>1.30 @x1; x1.5≥1.25; x2≥1.00; cadence 2–5/wk elapsed; confirmed suite separate.

### Live-tick P50 lot-scale (this session)

| Book | run_id | lot_p50 | $/trade | x1 PF | x1.5 PF | x2 PF | GOAL cost-stress |
|---|---|---:|---:|---:|---:|---:|---|
| **MaxKZ2** | `20260714_192304` | 0.5 | 2.309 | **1.275** | **1.246** | 1.218 | **FAIL** |
| A1 | `20260714_002505` | 0.5 | 2.309 | **1.284** | 1.255 | 1.227 | **FAIL** (x1) |
| RR2 | `20260714_194221` | 0.5 | 2.309 | 1.323 | 1.297 | 1.271 | PASS (partial only) |
| Spark100k | `20260714_193358` | 1.0 | 4.618 | 1.311 | 1.278 | 1.245 | PASS (partial only) |

### Aggregated-capture P50 (authoritative MaxKZ2 fail-closed sibling)

| Book | x1 / x1.5 / x2 | Verdict |
|---|---|---|
| MaxKZ2 `192304` | **1.267 / 1.235 / 1.204** | **FAIL** |
| RR2 `194221` | 1.316 / 1.286 / 1.257 | PASS diagnostic |

**Confirmed?** **NO** under both models. Demo never elevated.

## 5) Pass / fail / next

| Item | Result |
|---|---|
| Real login | **PASS** (verified) |
| Full QFSI | **FAIL** `STOP_DATA_FRONTIER` |
| MaxKZ2 priority#1 after Real cost | **FAIL** → `PARK_FAIL_PARTIAL_REAL_COST` — **no densify** |
| A1 under same partial cost | **FAIL** x1 PF |
| RR2 / Spark100k | partial-Real cost-stress **PASS** only — not confirmed / not GOAL |
| MaxKZ2+Spark compose promote | **blocked** (parent MaxKZ2 FAIL) |

**Next (evidence-honest):**
1. Keep Real connected; let `004_EXTENSION` finish / accumulate quotes (hygiene). Full QFSI still needs ≥90d + ≥30 commission/symbol + ≥100 slippage — Owner account history currently cannot clear USDJPY commission (0).
2. MaxKZ2 stays PARK under Real partial cost — do not densify / do not run confirmed ceremony on a FAIL parent.
3. R&D headline: independent thick-edge discovery (stub `HYP-H4-OUTSIDE-REV-001` needs prereg) — not QFSI-wait stall.
4. Exclusive Model 0 rebind only if Owner closes Real `terminal64` (alpha.ps1 fail-closed) — optional, not discovery blocker.

## 6) Files updated / produced this session

- `preflight/v4_data/20260714_MT5_READONLY_PROBE_V6_OWNER_LOGIN.json`
- `preflight/v4_data/20260714_EXECUTION_DATA_INVENTORY_V6.json`
- `…/20260714_DEAL_HISTORY_IMPORT_V2/` (+ import manifest)
- `preflight/20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_RECEIPT.json` (refreshed live-tick)
- `preflight/20260714_COSTSTRESS_*_REAL_P50*.json` / `*_LOTSCALE.json`
- `preflight/20260714_QFSI_REAL_REPRICE_A1_SPARK_LOTSCALE_RECEIPT.json` SHA `125101431A1AF88662230C61017B589643EB4DD39531966561035F278E9457A6`
- `02. AlphaFactory/tools/qfsi_real_reprice_a1_spark_lotscale.py`
- This deliverable; MaxKZ2 readout; `hot.md`; registry append
- Parallel authority kept: `readouts/20260714_MAXKZ2_QFSI_REAL_FAILCLOSED_DELIVERABLE.md`
