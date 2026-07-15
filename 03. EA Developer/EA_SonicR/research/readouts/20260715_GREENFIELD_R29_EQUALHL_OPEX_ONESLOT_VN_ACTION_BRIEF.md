# VN brief — Round 29 Equal-HL / OPEX / One-slot

Thời điểm: 2026-07-15 ~14:12 ICT
Ngoài R1–R28. **NON-FADE. NON-indicator.**

## Kết quả — `OFFLINE_ALL_KILL__NO_MODEL0`
| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-EQUAL-HL-BREAK-CONT-001` | 3566 | 1.0064 | 13.6778 | 0.9458 | KILL |
| `HYP-USDJPY-H1-OPEX-FRIDAY-CONT-001` | 76 | 1.3487 | 0.2915 | 1.2578 | KILL |
| `HYP-FX3-H1-ONESLOT-BOOK-ARCH-CONT-001` | 1299 | 0.8045 | 4.9825 | 0.7447 | KILL |

Receipt `4DCC400EA3A2E5CA7A735C31E29AB7F097B4036976381FCF09E3FC7204D28885`

## Cơ chế
1. Equal-HL break — double-tap thanh khoản rồi phá (structural)
2. OPEX Friday — thứ Sáu thứ 3 trong tháng (event)
3. One-slot book — tối đa 1 lệnh FX3, chọn |body|/ATR lớn nhất (architecture)

## Cost
autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R29 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

Best shelf RR2 `194548`. GOAL unmet.
