# Merge Memo — Hybrid ICT-Sonic indicator / zero-trade diagnosis

## Context

- `memo_id`: `MERGE_MEMO_20260715_HIS_ZERO_TRADE_INDICATOR_DIAG`
- `hypothesis_id`: `HYP-HYBRID-ICT-SONIC-M15-EURGBP-001` (parent — already `KILL_AT_MODEL0_EMPTY`)
- `packets_merged`: [red-team `2b140bb9`, research `7d27db1e`]
- `created_at`: 2026-07-15 ~16:55 ICT
- `created_by`: coordinator

## Receipts

| Role | Verdict | Confidence | Key finding |
|------|---------|------------|-------------|
| red-team | `MIXED` | high | #1 silent SL contradiction Dragon±40pip vs MaxSl 2.5×ATR; #2 AND-stack; Dragon/CopyBuffer/TimeGMT/spread NOT sole zeros |
| research | `CANDIDATES` (DIAG only) | med | Kill chain NearLevel∩Dragon∩Wave∩PVSRA then SL veto; offline gate-count before new Model 0 |
| impl / qc | not spawned | — | write blocked until Owner picks A/B/C |

## Conflicts

- Conflict order: gates > quant > systems > trader intuition
- Notes: Both agree parent empty is **valid fail** (HQ 100%, large sample). Red-team elevates **exec/logic SL bug** to rank 1; research elevates **NearLevel∩Dragon** as first structural zero with SL as silent finisher. Coordinator merge: **both real** — SL contradiction is a code-level always-on veto when Dragon buffer is folded into SL; AND-stack explains why remints still never printed pending.

## Decision (exactly one)

`PROBE`

- Rationale:
  1. Indicators themselves (iMA Dragon, ATR, CopyBuffer shift=1) are **not misaligned**.
  2. Quant: for ATR ≤16 pips (typical EURUSD M15), `40 pip` Dragon SL floor **always** exceeds `2.5×ATR` → silent `return` before `PlacePending` even if signal stack fires.
  3. Separately, NearLevel + Dragon + Wave + PVSRA on one closed bar is overconstrained (matches no pending prints if stack never clears).
  4. Do **not** densify Dragon 30–38 / hour veto / rescue parent hyp.

- Next move (Owner):
  - **A** — Offline Python sequential gate counts only (recommended first)
  - **B** — Authorize `HYP-HIS-DIAG-GATECOUNT-M15-EUR-001` after A
  - **C** — Stop Hybrid lane; new mechanism outside Classic Dragon revive

- `hot.md` updated: yes
