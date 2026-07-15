# VN brief — Round 26 Heikin / Keltner / Supertrend

Thời điểm: 2026-07-15 ~14:06 ICT
Ngoài R1–R25. **NON-FADE.** Không densify H4-engulf near-miss.

## Kết quả — `OFFLINE_ALL_KILL__NO_MODEL0`
| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-HEIKIN-STREAK-CONT-001` | 3826 | 1.0347 | 14.6751 | 0.9685 | KILL |
| `HYP-EURUSD-H1-KELTNER-WALK-CONT-001` | 807 | 1.0591 | 3.0953 | 0.9913 | KILL |
| `HYP-USDJPY-H1-SUPERTREND-FLIP-CONT-001` | 626 | 1.0971 | 2.4011 | 1.0237 | KILL |

Receipt `79F64DA0C028D3B6DA29F9FAE8CBEBCA634D8BD8E155895531C22DD9F3765A66`

## Cơ chế
1. Heikin streak — màu HA liên tiếp (≠ streak close thô)
2. Keltner walk — đi ngoài kênh (≠ Donch/RangeP80)
3. Supertrend flip — lật trail ATR (≠ ER/AC)

## Cost
autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R26 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

Best shelf RR2 `194548`. GOAL unmet.
