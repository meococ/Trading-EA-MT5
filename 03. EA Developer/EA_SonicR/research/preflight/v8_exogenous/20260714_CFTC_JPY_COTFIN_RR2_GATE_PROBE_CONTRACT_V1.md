# CFTC JPY FinFut COT → RR2 allow-gate probe contract V1

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority
Dichotomy-break data-surface mandate. GPT waived. Panel SHA `93D69F957A503B38C729F41D2E6B6D714A25EB330147383867C65A5EFC19AE54`.

## Signal (frozen a priori — GATE not entry)
1. Series: lagged `net_lev_money` from CFTC Financial Futures JAPANESE YEN.
2. available_at = observation_date + 4 calendar days.
3. z = (net - mean(prior 52 weekly avail)) / stdev; need >=40 prior.
4. Allow RR2 trade iff |z| >= 0.75 at decision date; else skip.
5. Do not mine z / lookback / market from readout.

## Kill
N<80 after gate OR tpw not in [1,6.5] OR PF<1.05 OR +$12 x1.5 PF<1.10 OR no stress lift vs ungated RR2.
