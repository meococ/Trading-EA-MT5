# Readout — HYP-SB-MAXHOLD-A2-001 Model 0

Date: 2026-07-14  
Run: `20260714_191628` (authoritative; empty twin `20260714_191429` discarded — race/empty report)  
EA: `EA_SilverBullet` / `EA_SilverBullet_v2.mq5`  
Verdict: **PARKED** — non-destructive vs A1; GOAL unmet

## Team critic merge (post-run)

- **Trader:** Max-hold is exposure hygiene; does not create setups. Cadence still ~2.0 floor-fail.
- **Quant:** PF 1.334 vs A1 1.344 (−0.01); net −4.2% vs A1; tpw 1.998 still &lt; 2.00 elapsed. Within non-destructive bar; not GOAL.
- **MQL5:** Overrides applied; Alpha `includes_sha256` closeout flake after report ready — artifacts kept.

## Binding

| Item | Value |
|---|---|
| Overrides | `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxHoldHours=30;InpUseMaxHold=1;InpUseWeekendFlat=1` |
| Matched baseline | A1 `20260714_002505` |
| Window | USDJPY M15 2021–2025 Deposit=100000 Model 0 |
| Cost | tester `current` / Demo — **not** Real QFSI |

## Metrics (`enhanced_summary.json`)

| Metric | A2 `191628` | A1 `002505` |
|---|---:|---:|
| Trades | 521 | 520 |
| PF | **1.334** | 1.344 |
| Net | **+$7540.77** | +7875.93 |
| Expectancy | +14.47 | +15.15 |
| Max DD % | ~0.85% | ~0.83% |
| tpw elapsed | **1.998** | 1.995 |

Offline probe SHA256 `D16181C2F29A2B4061889200EDF3EC76B3E4D1113060D1852582C5A561D5AE15` (near-null clip) confirmed by Model 0.

## Gates

| Check | Result |
|---|---|
| Kill floor | PASS |
| Non-destructive vs A1 | PASS (PF within −0.05; net within −10%) |
| Cadence ≥ 2.00 | **FAIL** (1.998) |
| GOAL / confirmed cost | **FAIL** |

## Banned next

No Friday cutoff mine, no NYPM (S153), no SkipFriday=0, no trail ON.

## Family budget

`silverbullet_management`: **2/2 used** (A1 weekend-flat + A2 max-hold). Remaining SB options → portfolio runner or rebuild entry Type — not more management knobs this campaign.
