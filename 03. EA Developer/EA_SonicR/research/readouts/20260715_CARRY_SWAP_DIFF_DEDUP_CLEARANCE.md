# De-dup — Carry/swap-aware multi-day differential

Status: **CLEARED**

| ID | ≠ killed |
|---|---|
| `HYP-FX3-CARRY-FUNDPROXY-MONTHU-HARVEST-001` | ≠ weekly single-pair Friday rebalance; ≠ daily rank deadband; ≠ 5bp event; ≠ Menkhoff vol; ≠ USBILL |
| `HYP-FX3-CARRY-FLUSH-MR-MULTIDAY-001` | ≠ rank/rebalance books; trigger = price flush vs carry; ≠ USBILL basket; ≠ vol-regime H4 strip |

## Intake ruling
Not pure duplicate: (1) Mon→Thu multi-symbol funding-floor harvest ≠ Friday single-winner weekly / daily deadband rank / 5bp event / Menkhoff; (2) flush→WITH-carry RR book ≠ rank rebalance and ≠ USBILL slope basket. Broker swap schedule absent → funding proxy labeled research-only.

## Broker swap
No reconstructable SWAP_LONG/SHORT history → funding proxy from G3 only.
