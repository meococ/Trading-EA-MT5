# V8 Autonomous Self-Research Campaign Closeout — 2026-07-13

Status: `NO_LEGAL_LOCAL_CANDIDATE / FAIL_CLOSED / NO_EA_BUILD / NO_MODEL_0`

## Process

Owner waived ChatGPT / GPT Deep Research. Local self-research used the G3
rates panel, COT TFF archives, frozen probe contracts, and Demo MT5 history
for falsification only. Evidence quality remained 1A fail-closed.

## Probes executed (all killed)

| Probe ID | Mechanism | Kill |
|---|---|---|
| `V8_CARRY_DIFF_WEEKLY_V1` | Friday D1 carry rank | cadence/sample (13t / 0.05/wk) |
| `V8_CARRY_DAILY_RANK_V1` | Daily D1 long/short carry | cadence/sample (68t / 0.261/wk) |
| `V8_CARRY_RATE_EVENT_5BP_V1` | ≥5bp G3 rate-event rebalance | cadence/sample (24t / 0.092/wk) |
| `V8_COT_TFF_SPEC_NET_CHG_V1` | Lagged TFF spec-net Δ / OI | fail beat return control / year concentration (cadence OK) |
| `V8_COT_TFF_LEVMONEY_H4_V1` | Lagged TFF lev-money net level H4 | stress-A PF 1.019 < 1.10 (cadence 2.51/wk; beats mom) |
| `V8_CARRY_VOL_REGIME_V1` | Menkhoff-style carry×vol H4 | stress-A PF 0.947; negative expectancy (cadence OK) |
| `V8_USBILL_SLOPE_USD_BASKET_V1` | US 26W−4W bill-slope → USD basket | year concentration 0.78 (PF-A 1.195 beat control) |

Campaign lane readout: `readouts/20260713_NO_LEGAL_LOCAL_CANDIDATE_READOUT.md`
(`NO_LEGAL_LOCAL_CANDIDATE`). Receipt:
`preflight/20260713_NO_LEGAL_LOCAL_CANDIDATE_RECEIPT.json`.

## Compile / Model 0

None authorized. No new registry row. No frozen prereg for a survivor.
`EA_CarryPublicRates` remains scaffold-only (prior compile SUCCESS ≠ gate pass).

## Required external-state change to reopen

1. New hash-bound exogenous panel (equity/bond differentials or true
   forwards/OIS) with lag/join contract **before** any probe; or
2. Owner Real-broker QFSI capture for cost provenance (necessary for later
   Model 0, insufficient alone).

Do not retune killed constants. Do not reopen V2–V7 price-only families.
Do not use ChatGPT ceremony for this lane unless Owner reverses the waiver.
