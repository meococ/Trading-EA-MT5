# VN brief — Round 31 Outside / FirstDOM / TimeStop-CD

Thời điểm: 2026-07-15 ~14:17 ICT
Ngoài R1–R30. **NON-FADE. NON-indicator.**

## Kết quả — `OFFLINE_ALL_KILL__NO_MODEL0`
| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-OUTSIDE-BAR-CONT-001` | 3278 | 0.9626 | 12.5732 | 0.9034 | KILL |
| `HYP-GBPUSD-H1-FIRST-DOM-CONT-001` | 17 | 0.3147 | 0.0652 | 0.2883 | KILL |
| `HYP-FX3-H1-POST-TIMESTOP-CD-ARCH-CONT-001` | 3896 | 0.9466 | 14.9436 | 0.881 | KILL |

Receipt `AAD9BA4043042D994B02AD9B1638C103C4FEE02000FEDC4232E8091D02527343`

## Cơ chế
1. Outside-bar CONT — nến bao trùm H+L rồi tiếp tục theo close (structural)
2. First-DOM — ngày giao dịch đầu tháng (event)
3. Post-timestop CD — sau time-exit chờ N bar mới vào lại (architecture)

## Cost
autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R31 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

Best shelf RR2 `194548`. GOAL unmet.
