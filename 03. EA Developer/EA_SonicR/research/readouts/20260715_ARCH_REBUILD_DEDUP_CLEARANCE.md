# De-dup clearance — architecture rebuild Track B

Date: 2026-07-15  
Authority: Owner STRATEGY PIVOT; EXO_FRED_DISPLACE_SPAM_PAUSED

## Objects

| ID | Class | Independence claim |
|---|---|---|
| `HYP-RR2-VOLTARGET-ATRRISK-001` | Sizing architecture on frozen RR2 `194548` | Reweights risk_usd to book median; **not** MaxKZ partial, **not** BE@1R, **not** RR/session densify, **not** COT/FRED gate |
| `HYP-RR2-H4-REGIME-ALIGN-GATE-001` | Multi-TF regime allow-gate on frozen RR2 | H4 ATR%ile band + EMA align; **not** M15 BE path, **not** USJP yield-z, **not** WALCL/PD/MMF/6J/ECB/Brent |

## Banned collisions

- Dichotomy BE@1R (`HYP-RR2-EXIT-BE1R-M15PATH-001`) — killed; this board does not revive BE.
- MaxKZ2 partial / RR retune / Spark MaxPerDay / session cuts.
- FRED displace/ToT / exo gate densify (spam paused).
- Wave1–9 price-twin reopen.

## Survivor bar

N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15 ∧ stress lift vs RR2 baseline x1.5.
Model 0 withheld unless `PROBE_SURVIVOR`.

## Clearance

**CLEARED** for offline probe only.
