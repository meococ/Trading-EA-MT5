# Offline probes — NYFed PD primary structural sleeve

Date: 2026-07-15  
Status: `OFFLINE_ALL_KILL / NO_MODEL0`  
Panel SHA: `946CE197290BE86FADACE548D98BCB0F879D51C8738A00381235BDDAD83981D5`  
Receipt: `7FFF201DA7756F6270AC1D2F329E80F92B9467ABDFB2656E2625ABFA882FA762`

## Objects (independent sleeve — not RR2 gate)

| ID | N | PF | tpw | x1.5 | Verdict |
|---|---|---|---|---|---|
| `HYP-USDJPY-H1-PD-GS-EXPAND-DISPLACE-001` | 481 | 0.9494 | 1.8439 | 0.8946 | KILLED_AT_OFFLINE_PROBE |
| `HYP-USDJPY-H1-PD-GS-CONTRACT-DISPLACE-001` | 412 | 1.0287 | 1.5794 | 0.9716 | KILLED_AT_OFFLINE_PROBE |
| `HYP-EURJPY-H1-PD-GS-EXPAND-DISPLACE-001` | 497 | 1.0571 | 1.9053 | 1.0003 | KILLED_AT_OFFLINE_PROBE |

## A priori

- PD lag: observation+8d (frozen `available_at`)
- Expand = `wow_delta_mn > 0`; contract otherwise; fail-closed if missing
- Displace: range≥1.2·ATR14, body≥0.55·ATR14, close frac 0.60, SL=1.0·ATR, RR=2, hold≤12 H1, ≤1/day
- **Do not** densify PD WoW sign or V9 expansion thresholds

## Model 0

Withheld (no PROBE_SURVIVOR).

## Cost track (parallel)

Verdict **GAP** — see `readouts/20260714_COST_SURFACE_TRACK_GAP_RECONFIRM.md`.
No RR2 re-stress under session surface (surface absent).

Best shelf RR2 `194548`. GOAL unmet.
