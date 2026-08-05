# AIRQMB Multi-9 M5 Logic-to-Code Matrix

Frozen before the first MT5 performance launch for this source identity.

## Bound artifacts

- EA source: `03. EA Developer/EA_AIRQMB_RegimeFusion/EA_AIRQMB_RegimeFusion.mq5`
- Source SHA-256: `A0622C7BCB22F1DBAABD707B1159679283D6B2C1AD0CFE642C5301E4573B1A81`
- EA EX5 SHA-256: `3F7824E9ABEDD4CC094B66EA5A747673A335E23AB9D3A7CAB83CD269ED810A84`
- AlphaFactory contract SHA-256: `1FDC453718A1D306AB67D686AAD4B96B892A9B45400CF267136A4071211C81E5`
- QQE source / runtime EX5: `1C56F8AC35E322140B26F81530932809E261B1439970B27509E7060F8A814EAB` / `6899A8AC08523B8026010A2095A4D36B6508318E0EDF3D8B39DC52170F28F265`
- MBB source / runtime EX5: `65545F5A9ABC5FD1DA2992897C6495CF0A7ACD555036FEF544379F5A565C82C4` / `D5564EBBB25199138F40CC0449172C8BAFC2F12854E5B5E18B861C4AD21167D2`
- AIRD source / runtime EX5: `33BBE35AA63AA03C47678BB048EFE625E40497D34B28A56148DE10470EF1AEDC` / `E030D2F1E09B86226CE2AECCA5905052BA34AD12EA0635FB50EAFE4A6A51A129`

## Signal matrix

All indicator reads use `CopyBuffer(..., shift >= 1)` and orders are evaluated once at the first tick of the next M5 bar.

| AI held regime | MBB event | QQE confirmation | Action |
|---|---|---|---|
| `RANGING (2)` | `S1 long` | both smoothed RSI lanes rising and at least one `<= -3` | buy |
| `RANGING (2)` | `S1 short` | both smoothed RSI lanes falling and at least one `>= +3` | sell |
| `BULL (0)` | `S3 long`, else `S2 long` | both RSI lanes above zero; QQE composite non-negative | buy |
| `BEAR (1)` | `S3 short`, else `S2 short` | both RSI lanes below zero; QQE composite non-positive | sell |
| `HIGH VOL (3)` | any | any | no new position |

Every lane additionally requires AIRD `valid=1`, confidence at or above the frozen threshold, valid MBB geometry and no owned/foreign symbol exposure.

## Risk and lifecycle matrix

| Concern | Frozen rule |
|---|---|
| Initial stop | `max(MBB half-width * 1.00, 3 * live spread, broker stops level + 2 points)` |
| Initial target | `1.50R` |
| Position size | loss at stop equals at most `0.25%` current equity; broker step floored |
| Margin reserve | requested margin at most `50%` current free margin; volume may only decrease |
| Cost gate at entry | live spread / stop distance `<= 0.15` |
| Concurrency | one same-symbol position; foreign symbol position blocks mutation |
| Frequency | maximum 3 entries per UTC day; 5-bar entry cooldown |
| Session | new entries from `07:00` until before `20:00` UTC |
| Exposure | daily flat `20:00` UTC; Friday flat `20:00` UTC; max hold 48 M5 bars |
| Locks | daily equity loss `3.5%`; peak equity drawdown `8%` |
| Telemetry | lifecycle-v3 open/final-close rows plus run-meta funnel |

## Implementation mapping

- `ReadSnapshot`: closed-bar indicator contract and warm-up gate.
- `BuildDecision`: regime-specific signal matrix and price geometry.
- `RiskSizedVolume`: loss-based size plus free-margin reduction.
- `SubmitEntry`: checked market order with initial SL/TP.
- `ManagePosition`: time, daily and Friday exits.
- `LogLifecycleDeal`: report/deal/lifecycle reconciliation evidence.

No outcome-driven session pruning, weekday pruning, direction inversion, indicator retuning or symbol pooling is authorized under the baseline identities.

