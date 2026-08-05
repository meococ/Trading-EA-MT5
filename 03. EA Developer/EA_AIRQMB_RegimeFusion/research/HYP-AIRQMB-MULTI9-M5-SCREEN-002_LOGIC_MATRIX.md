# AIRQMB Multi-9 M5 SCREEN-002 Logic-to-Code Matrix

Frozen before any SCREEN-002 MT5 launch.

## Identity

- EA source SHA-256: `07D94050A8142353E6E0DD491334CED5631E3B0EF12011B8119AD92A28208B52`
- AlphaFactory contract SHA-256: `1FDC453718A1D306AB67D686AAD4B96B892A9B45400CF267136A4071211C81E5`
- QQE source/runtime: `1C56F8AC35E322140B26F81530932809E261B1439970B27509E7060F8A814EAB` / `6899A8AC08523B8026010A2095A4D36B6508318E0EDF3D8B39DC52170F28F265`
- MBB source/runtime: `65545F5A9ABC5FD1DA2992897C6495CF0A7ACD555036FEF544379F5A565C82C4` / `D5564EBBB25199138F40CC0449172C8BAFC2F12854E5B5E18B861C4AD21167D2`
- AIRD source/runtime: `33BBE35AA63AA03C47678BB048EFE625E40497D34B28A56148DE10470EF1AEDC` / `E030D2F1E09B86226CE2AECCA5905052BA34AD12EA0635FB50EAFE4A6A51A129`

EX5 is snapshotted and hashed per AlphaFactory run but is not a durable prereg key because MetaEditor output is not byte-deterministic across recompiles of unchanged source.

## Closed-bar decision matrix

| AIRD held regime | MBB event | QQE condition | Action |
|---|---|---|---|
| Range `2` | S1 long | both RSI lanes rise; at least one `<= -3` | buy |
| Range `2` | S1 short | both RSI lanes fall; at least one `>= +3` | sell |
| Bull `0` | S3 long, else S2 long | both RSI lanes `>0`, composite non-negative | buy |
| Bear `1` | S3 short, else S2 short | both RSI lanes `<0`, composite non-positive | sell |
| High-vol `3` | any | any | no entry |

Every indicator decision reads shift 1 or 2 only. Entry is submitted on the first tick of the next M5 bar.

## Execution and risk

- AIRD confidence: `0.45` baseline.
- Stop: `max(1.00 * MBB half-width, 3 * spread, broker stop level + 2 points)`.
- Target: `1.50R`; risk: at most `0.25%` equity.
- Spread/stop `<=0.15`; 5-bar cooldown; maximum 3 entries/day.
- Entry window `07:00–20:00 UTC`; daily and Friday flat `20:00 UTC`; max hold 48 bars.
- Daily loss lock `3.5%`; peak-equity drawdown lock `8%`.
- One owned position per symbol; foreign symbol position blocks mutation.
- lifecycle-v3 telemetry is mandatory.

Tick processing is intentionally minimal: the EA increments its tick counter and checks the M5 bar clock. UTC conversion, account locks, position scans, indicator reads and decisions run once per new bar. Initial SL/TP remains server/tester tick-accurate.

