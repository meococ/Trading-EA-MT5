# QFSI Capture Continue Coordinator — 2026-07-14

Status: **`PARTIAL`**  
Process: GPT waived · nested `cursor-grok-4.5-high-fast` · no-Git · no densify  
GOAL claim: **false** · confirmed claim: **false**

## Verdict

No-live Real capture **continued and extended**. Full QFSI verified-cost
reprice for MaxKZ2 remains **blocked** (eligible bundles = 0). A separate
**partial** Real cost-stress path was run with explicit caveats (live USDJPY
spread + EURUSD commission clue N=2 transferred; slippage MISSING ≠ 0). That
is **not** verified cost / not `GO_FOR_PREREG`.

## Live capture status

| Window | Status | Quotes / HB | Commission (E/G/X/U) | Slippage |
|---|---|---:|---|---:|
| `20260714_QFSI_REAL_001` | COMPLETE_PARTIAL | 116 / 116 | 2 / 0 / 0 / **0** | 0 |
| `20260714_QFSI_REAL_002` | COMPLETE_PARTIAL | 421 / 440 | 2 / 0 / 0 / **0** | 0 |
| `20260714_QFSI_REAL_003_CONTINUATION` | COMPLETE_PARTIAL (~30m) | 3376 / 3444 | 2 / 0 / 0 / **0** | 0 |
| `20260714_QFSI_REAL_004_CONTINUATION` | COMPLETE_PARTIAL (~20m race) | 2267 / 2296 | 2 / 0 / 0 / **0** | 0 |
| `20260714_QFSI_REAL_004_EXTENSION` | **RUNNING** (7200s) | growing | same history export | 0 |

Symbols: EURUSD, GBPUSD, XAUUSD, USDJPY. Stop:
`evidence/execution/FivePercentOnline-Real/STOP_QFSI_CAPTURE.flag`.

003 inspect (while running → completed): PID 57232; validation
`STOP_DATA_FRONTIER`; manifest SHA
`821925CB549E47C1B861D03C95DB2CD6179589550E1F6996B38E719081BDFA04`.

## Inventory V4

| Field | Value |
|---|---|
| Path | `preflight/v4_data/20260714_EXECUTION_DATA_INVENTORY_V4.json` |
| SHA256 | `36155302C7372C228585589DB09A2E7115C9AF375475AB8646CE26E4FE802009` |
| Manifests / validated / eligible | 3 / 3 / **0** |
| Verdict | `STOP_DATA_FRONTIER` |

## Remaining gates vs 90d eligibility (honest)

| Gate | Required | Observed | Status |
|---|---|---|---|
| Quote elapsed days | ≥90 | ≪1 day | **FAIL** |
| Commission / symbol | ≥30 | EURUSD=2; others=0; **USDJPY=0** | **FAIL** |
| Slippage fills / symbol | ≥100 (≥30 buy/sell) | **0** (MISSING) | **FAIL** |
| Eligible hash-bound bundle | ≥1 | **0** | **FAIL** |

Passive no-live capture can grow quotes/heartbeats overnight/days, but
**cannot** invent USDJPY commission lifecycles or independent pre-send
slippage refs. Those need legitimate Real account history / broker execution
reports under the contract.

## Partial Real reprice (caveated)

Tool: `qfsi_real_reprice_rr2_maxkz2.py`  
Receipt SHA: `69CFE2392131D5E1FE633BA5B767BE868FD6E34EF231A531D550197D80877AEA`  
Cost label: `REAL_LIVE_SPREAD_PLUS_EURUSD_COMMISSION_CLUE`  
Base ≈ **$2.31**/trade P50 · **$2.62** P90 (lot 0.5; slip MISSING).

| Book | x1 PF | x1.5 PF | x2 PF | GOAL cost-stress |
|---|---:|---:|---:|---|
| RR2 `20260714_194221` | 1.323 | 1.297 | 1.271 | **PASS** (partial only) |
| MaxKZ2 `20260714_192304` | 1.275 | 1.246 | 1.218 | **FAIL** |

Decision: `MIXED_PARTIAL_REAL_COST_ONE_SURVIVOR_PATH_FULL_QFSI_STILL_OPEN`.

Verified-cost MaxKZ2 reprice: still
`BLOCKED_REPRICE_WAITING_VERIFIED_COST`. Do **not** densify MaxKZ from this
partial FAIL. Do **not** claim GOAL.

## Next

1. Keep Real login; let `004_EXTENSION` finish (~2h) or stop via flag.
2. Re-inventory after extension closes; expect eligible still 0 until sample
   gates clear.
3. Full verified reprice only after eligible bundle (or Owner-supplied broker
   execution report with independent refs).
4. Parallel R&D: `HYP-H4-OUTSIDE-REV-001` stub (prereg before code) — not densify.

## Paths

- Receipt: `preflight/20260714_QFSI_CAPTURE_CONTINUE_RECEIPT.json`
- Partial reprice receipt: `preflight/20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_RECEIPT.json`
- Deliverable: `readouts/20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_DELIVERABLE.md`
- Checklist: `preflight/20260714_MAXKZ2_QFSI_REPRICE_CHECKLIST.md`
- Evidence: `02. AlphaFactory/evidence/execution/FivePercentOnline-Real/`
