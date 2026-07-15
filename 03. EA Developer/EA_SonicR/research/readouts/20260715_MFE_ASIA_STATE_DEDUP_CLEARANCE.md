# De-dup clearance — MFE stall-cut + Asia→London state-machine

Date: 2026-07-15  
Authority: Owner post-pivot arch lane; `EXO_FRED_DISPLACE_SPAM_PAUSED`

## Objects

| ID | Class | Independence claim |
|---|---|---|
| `HYP-RR2-EXIT-MFE-STALLCUT-M15PATH-001` | Path-dependent exit on frozen RR2 `194548` | Hard-exit after MFE arm@0.75R + stall/giveback; **≠** BE@1R (no SL→entry); **≠** MaxKZ/RR densify; **≠** vol-target / H4 regime |
| `HYP-USDJPY-H1-ASIA-PCTL-COIL-LONDON-BREAK-STATE-001` | New entry state-machine USDJPY H1 | Relative Asia-range p40 coil → London H/L break + EXPIRE; **≠** ATR-bar continuation (intake-fail); **≠** NZD Wave7 densify twin (adds relative coil + EXPIRE + RR=2 USDJPY); **≠** EUR Asia-box / XAU Asia-compress; **≠** RR2 hour densify |

## Intake fail (documented, not densified)

| ID | Result |
|---|---|
| `HYP-USDJPY-H1-ASIA-COIL-LONDON-CONT-STATE-001` | `INTAKE_FAIL_EMPTY` — AsiaRange vs 1-bar ATR@0.60 → n_coil=0 |

## Banned collisions

- Dichotomy BE@1R (`HYP-RR2-EXIT-BE1R-M15PATH-001`) — killed; this board does **not** revive BE.
- Vol-target / H4 regime (prior KILL board) — different mechanism.
- Wave5 EUR Asia-box / Wave7 NZD Asia-London / MULTISYM XAU Asia-compress densify.
- FRED displace/ToT / exo densify (spam paused).
- MaxKZ2 / RR / session / coil-percentile mining from this readout.

## Survivor bar

N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15.  
RR2 child additionally requires stress lift vs RR2 baseline x1.5.  
Model 0 withheld unless `PROBE_SURVIVOR`.

## Clearance

**CLEARED** for offline probe only (MFE + Asia pctl-coil variant).
