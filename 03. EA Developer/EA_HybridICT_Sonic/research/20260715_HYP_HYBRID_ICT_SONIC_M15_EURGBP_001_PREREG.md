# HYP-HYBRID-ICT-SONIC-M15-EURGBP-001 — Prereg (Owner Path-C stub)

**Status:** Owner override stub — NOT de-dup cleared. Not promotion authority.

| Field | Frozen value |
|---|---|
| hypothesis_id | `HYP-HYBRID-ICT-SONIC-M15-EURGBP-001` |
| package | `EA_HybridICT_Sonic` |
| symbols | EURUSD, GBPUSD |
| timeframe | M15 |
| dragon | EMA34 High/Mid/Low |
| HTF | H4 BOS + FVG/OB/liq |
| RR | 2.5 |
| risk | 0.25%/trade; daily loss 2%; max 5/day |
| session | 07–20 (GMT flag) |
| spread | ≤2.5 pips |
| pending | 4 pips beyond extreme; TTL 4 bars |

## Kill gates (a priori, for later Model 0)

- PF x1 < 1.30 OR x1.5 < 1.25 → KILL
- elapsed tpw outside 2–5 → KILL
- non-repaint / lookahead fail → KILL
- No post-hoc hour/day veto rescue

## Explicit notes

- Tick-volume PVSRA is a **proxy**, not true PVSRA master.
- News filter not wired (OFF).
- Owner accepted revive-risk Path-C; prior PARK memo is critique only.
