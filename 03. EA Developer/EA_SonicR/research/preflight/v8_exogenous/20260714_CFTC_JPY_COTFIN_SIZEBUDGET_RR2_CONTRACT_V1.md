# CFTC JPY FinFut COT → RR2 size-budget allow-gate V1

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority
Data-surface / QFSI hygiene lane post dichotomy+|z| KILL. GPT waived.
Panel SHA `93D69F957A503B38C729F41D2E6B6D714A25EB330147383867C65A5EFC19AE54`.

## Signal (frozen a priori — GATE not entry; NOT |z|)
1. Series: lagged `net_lev_money` for `JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE` (panel available_at already +4d).
2. Lookback = 52 prior available weeks.
3. Allow RR2 trade iff `abs(net_lev_money)` <= median(abs(net) over prior 52).
4. Rationale: size-budget / anti-crowd — avoid oversized speculative positioning; independent of z-score extremity.
5. Do not mine threshold / lookback / market from readout.

## Kill
N<80 after gate OR tpw not in [1,6.5] OR PF<1.05 OR +$12 x1.5 PF<1.10 OR no stress lift vs ungated RR2.
