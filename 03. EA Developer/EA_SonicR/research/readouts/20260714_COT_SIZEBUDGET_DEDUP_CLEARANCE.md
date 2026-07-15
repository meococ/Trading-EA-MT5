# De-dup Clearance — HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001

## Against killed parent
- **Killed:** `HYP-RR2-CFTC-JPY-LEVMONEY-ZGATE-001` (OFFLINE_KILL; cadence + stress; skip-gate)
- **New:** `HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001`

## Orthogonal axes (not a clone)

| Axis | Z-GATE (killed) | SIZEBUDGET (this) |
|---|---|---|
| Decision type | Allow/skip GATE | SIZE BUDGET (scale risk/PnL) |
| Trade retention | Drops trades when crowded | Keeps ALL RR2 trades |
| Crowding score | |z| of net_lev_money vs history | Percentile rank of \|net_lev_money\| among prior 52 weeks |
| Missing history | Gate fail-closed / drop | Fail-open size_mult=1.00 (no skip) |
| Cost stress | Flat BASE_COST on kept trades | BASE_COST * stress_mult * size_mult |
| Cadence impact | Reduces N/tpw (killed on cadence) | Preserves baseline cadence |

## Clearance
Cleared for offline probe: same panel SHA, different semantics (size vs gate), different score (|net| percentile vs |z|), no trade skip.
