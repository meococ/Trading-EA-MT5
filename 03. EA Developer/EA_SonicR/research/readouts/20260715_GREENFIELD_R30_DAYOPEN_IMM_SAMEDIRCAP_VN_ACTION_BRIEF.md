# VN brief — Round 30 Day-Open / IMM / SameDir-Cap2

Thời điểm: 2026-07-15 ~14:15 ICT
Ngoài R1–R29. **NON-FADE. NON-indicator.**

## Kết quả — `OFFLINE_ALL_KILL__NO_MODEL0`
| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-PRIOR-DAY-OPEN-BREAK-CONT-001` | 1579 | 1.0011 | 6.0564 | 0.9373 | KILL |
| `HYP-EURUSD-H1-IMM-WEDNESDAY-CONT-001` | 27 | 1.0405 | 0.1036 | 0.9592 | KILL |
| `HYP-FX3-H1-SAMEDIR-CAP2-ARCH-CONT-001` | 3896 | 0.9393 | 14.9436 | 0.8748 | KILL |

Receipt `DD7FE049B2D3B35F19C21F3649B99F3C750F747BE5647C463FFAD6866522F635`

## Cơ chế
1. Prior-day OPEN break — phá open ngày UTC trước (structural)
2. IMM Wednesday — Wed thứ 3 Mar/Jun/Sep/Dec roll FX futures (event)
3. SameDir Cap2 — tối đa 2 lệnh cùng chiều FX3 (architecture)

## Cost
autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R30 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

Best shelf RR2 `194548`. GOAL unmet.
