# De-dup clearance — London–NY overlap EUR/GBP

Date: 2026-07-15
Authority: post MFE/Asia ALL_KILL; `EXO_FRED_DISPLACE_SPAM_PAUSED`
Status: `A_PRIORI_CLEARANCE_BEFORE_PROBE`

## Objects

| ID | Class | Independence claim |
|---|---|---|
| `HYP-EURUSD-H1-LONDON-IMBAL-NY-FADE-001` | London mid-imbalance → NY fade | Fade to London mid in 13–16; **≠** MULTISYM EUR 07–10 continue-break; **≠** AUD overlap fail-fade; **≠** ORB/IB/LORBA |
| `HYP-GBPUSD-H1-LONDON-COIL-NY-BREAK-001` | London relative coil → NY break | p40/60 LondonRange → fire 13–16 H/L break; **≠** GBP NY-impulse body≥1.2ATR; **≠** EUR overlap-break; **≠** Asia-coil densify |
| `HYP-GBPUSD-H1-EURUSD-LEAD-OVERLAP-CATCHUP-001` | EUR lead → GBP lag catch-up | Lead EUR 11/12 + GBP quiet → GBP fire 13–15; **≠** EURGBP→EURUSD lead; **≠** JPY-cross catch-up; **≠** Spark/ITSM |

## Kill shelf (do not retune)

IB · ORB · NY-IB · Failed ORB · LORBA · Spark · ITSM session spam · MULTISYM EUR London-overlap continue-break · MULTISYM GBP NY-open impulse · AUD overlap fail-fade · USDJPY London mid-reclaim / drive-fail / LondonNY PB · EUR Asia-box · MaxKZ/RR · FRED exo · RR2 exit-path · Asia densify.

## Survivor bar

N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15.
Model 0 withheld unless `PROBE_SURVIVOR`.

## Clearance

**CLEARED** for offline probe only (3 LNY EUR/GBP objects).
