# Readout — HYP-ITSM-PULLBACK-M15-001 / EA_ITSM

Date: 2026-07-14  
State: `near_miss` (Model 0 screen; cadence OK; PF below Owner iterate floor 1.20 and GOAL 1.30)  
Process: `GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY`

## Run

| Field | Value |
|---|---|
| run_id | `20260714_003920` (authoritative); twins `20260714_003635` / `20260714_003735` identical metrics |
| EA | `EA_ITSM` (pinned existing; not a new wrapper) |
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Spread | tester `current` (research-proxy; not broker-verified) |
| History quality | 99% |
| Seed | `S509 / EA_ITSM` USDJPY NY-only RR2.0 (PF~1.22, ~2.35/wk) |
| Path | `02. AlphaFactory/runs/EA_ITSM/20260714_003920/` |
| Report SHA256 | `97D3B57DB9269DAA930C58E34A27A675C51A8388292846F8C22F918983C3B079` |
| Overrides | `InpRiskPct=0.5;InpRR_Ratio=2.0;InpMaxTradesDay=2;InpTradeFri=0` (equiv. alpha-normalized order OK) |

Frozen defaults observed: KZ1 `[09,12)` + KZ2 `[15,18)`, Mon–Thu / Fri off, confluence filters OFF (`InpUseMACD/RSI/ADX/...=false`), RR 2.0, risk 0.5%.

Alpha closeout threw `includes_sha256` mismatch after report ready (same class as other 2026-07-14 Model 0 screens); artifacts retained.

## Metrics (tester report)

| Metric | Value |
|---|---|
| Profit factor | **1.16** |
| Total trades | **852** |
| Net profit | **+$3,959.60** |
| Expectancy | **+4.65** |
| Max equity DD | **9.25%** |
| Elapsed calendar weeks | 1825/7 ≈ **260.71** |
| Trades/week (elapsed) | 852 / 260.71 ≈ **3.27** |

## Verdict

- **PF:** FAIL Owner iterate floor (1.16 < 1.20). Also FAIL GOAL research bar (1.16 < 1.30). Survives prereg hard kill (`PF >= 1.00`).
- **Cadence:** PASS (3.27 in prereg `[1.5, 6.0]` and above GOAL 2.0 floor). Stronger than seed ~2.35/wk on this denser LDN+NY package.
- **Owner rule pack:** PF≥1.20 ∧ cadence≥1.5 → iterate candidate: **NO**. Both fail → kill: **NO**. PF>1.30 ∧ cadence≥2 → GOAL-near: **NO**.
- **Cost honesty:** research-proxy tester `current` only — **not** Real QFSI; missing commission/slippage ≠ 0.
- **Overall:** **NEAR_MISS / PARK**. Independent of SparkAsian (parked PF1.31 / 1.25wk). Do **not** claim GOAL / confirmed / validate-full.

## Banned rescue

Do **not** enable confluence (MACD/ADX/H4/etc.) from this readout, skip-Tue densify, hour/day mining, or retune RR/risk from killed T10 variants (`S510–S543`). Do not edit ITSM into a post-hoc Spark/SB rescue.

## Next

Park denser ITSM as cadence-strong / edge-weak near-miss. Prefer a new independent family or Owner Real QFSI for parked SB/Spark; do not ChatGPT Deep Research.
