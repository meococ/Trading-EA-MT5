# Probe Design Freeze — US–EU Bond/Policy Diff Shock H4 V1

Status: `FROZEN_PRE_RESULT / INDEPENDENT`  
Date: 2026-07-13

## Independence

Not weekly FX carry rank; not money-market Δcarry event book; not H4 carry-level
strip. Mechanism: innovations in **US 2y Treasury yield vs EUR policy/deposit
proxy** as a capital-market / rates-path differential for EURUSD only
(Menkhoff-adjacent funding/risk channel via bond–policy wedge).

## Frozen constants

| Constant | Value |
|---|---|
| Symbol | EURUSD only |
| State | lagged(DGS2) − lagged(ECB DFR) |
| Trigger | \|Δ state\| ≥ 5 bps |
| Decision | next H4 after available day |
| HOLD_BARS | 12 |
| Weekend flat | Friday hour >= 16 UTC |
| Cost A/B | 1.5 / 3.0 pip |
| Train/holdout | 2018–2022 / 2023–2025 |
| Lags | DGS2 +1d; ECB DFR +1d |
| Control | same events; direction = sign(20 H4 return) |
| Direction | sign(new state) after change (positive => long EURUSD) |

## Train gates

trades>=100; 1.5<=tpw<=5.0; PF_a>=1.10; beat control; expectancy_a>0.
