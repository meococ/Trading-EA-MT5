# Prereg — HYP-H1-LOWVOL-DONCHIAN-MR-001

Date: 2026-07-14  
State: `preregistered`  
Family: `h1_lowvol_donchian_mr` · budget **1/1** this campaign  
Unlock: Owner aggressive-refine mandate overrides Demo diminishing-returns pause for this stub.

## Thesis

When H1 ATR is compressed vs its slow baseline (`ATR14/SMA50(ATR) ≤ 0.85`), fade
Donchian(20) extremes toward the channel mid on closed bar[1]. Mon–Thu, weekend
flat, risk 0.5%.

## De-dup

| Contrast | Difference |
|---|---|
| `HYP-H1-ATR-REGIME-MOM-001` | Opposite vol gate + fade vs continuation |
| EMA Stretch Fade M15 | H1 Donchian object, not EMA20 stretch |
| Chop / ADR / ORB / PDH / SB | Different structure |

## Locked design

| Item | Value |
|---|---|
| EA | `EA_H1LowVolDonchianMR` |
| Symbol/TF | USDJPY H1 |
| Window | 2021.01.01–2025.12.31 Model 0 Deposit 10000 |
| ATRRatioMax | 0.85 |
| Donchian | 20; extreme frac 0.05 |
| Risk | 0.5%; TP mid-prefer / 1.5R; SL beyond channel |
| Days | Mon–Thu; Fri off |
| Magic | 880951 |
| Overrides | `` (defaults) |

## Gates

Kill: PF<1.00 or tpw∉[1.0,6.0] or N<80.  
Park: PF∈[1.00,1.30) cadence OK.  
HIT_RESEARCH: PF>1.30 and tpw∈[2.0,5.0] (unconfirmed).

Banned: ATR/Donchian/hour/day mining after readout.

## Team critic memo (pre-run)

- **Trader:** Low-vol mean-reversion is a real regime; Donchian fade is classic.
- **Quant:** Opposite of parked mom sleeve — independent Type; still Demo cost.
- **MQL5:** Closed-bar Donchian uses shifts 1..N only; non-repaint OK.
